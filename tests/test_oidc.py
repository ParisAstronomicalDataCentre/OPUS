#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Unit tests for the OpenID Connect access tokens accepted by the UWS server (Bearer),
with a simulated Identity Provider (no network)
"""

import base64
import time

import pytest
import webtest
from joserfc import jwt
from joserfc.jwk import OctKey, RSAKey

from uws_server import oidc, uws_server

settings = uws_server.settings
test_app = webtest.TestApp(uws_server.app)

ISSUER = "https://iam.test/"
DISCOVERY = ISSUER + ".well-known/openid-configuration"


class FakeIdP:
    """Simulated Identity Provider: discovery, keys, userinfo, and signed tokens"""

    def __init__(self):
        self.key = RSAKey.generate_key(2048, parameters={"kid": "k1"}, private=True)
        self.userinfo = {}  # access token -> userinfo
        self.calls = {"discovery": 0, "jwks": 0, "userinfo": 0}

    def token(self, key=None, **claims):
        payload = {"iss": ISSUER, "sub": "sub-1", "exp": int(time.time()) + 300, **claims}
        key = key or self.key
        return jwt.encode({"alg": "RS256", "kid": key.kid}, payload, key)

    def get(self, url, headers=None, timeout=None):
        class Response:
            def __init__(self, data, status=200):
                self.data, self.status_code = data, status

            def json(self):
                return self.data

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise oidc.requests.HTTPError(self.status_code)

        if url == DISCOVERY:
            self.calls["discovery"] += 1
            return Response({"issuer": ISSUER, "jwks_uri": ISSUER + "jwks", "userinfo_endpoint": ISSUER + "userinfo"})
        if url == ISSUER + "jwks":
            self.calls["jwks"] += 1
            return Response({"keys": [self.key.as_dict(private=False)]})
        if url == ISSUER + "userinfo":
            self.calls["userinfo"] += 1
            token = (headers or {}).get("Authorization", "")[len("Bearer "):]
            return Response(self.userinfo[token]) if token in self.userinfo else Response({}, 401)
        raise AssertionError(f"unexpected request {url}")


@pytest.fixture
def idp(monkeypatch):
    fake = FakeIdP()
    monkeypatch.setattr(oidc.requests, "get", fake.get)
    monkeypatch.setattr(settings, "OIDC_IDPS", [{"title": "IAM", "url": DISCOVERY}])
    oidc._providers.clear()
    oidc._userinfo.clear()
    return fake


class TestAccessToken:

    def test_email_from_userinfo(self, idp):
        token = idp.token()
        idp.userinfo[token] = {"sub": "sub-1", "email": "Alice@Example.org"}
        assert oidc.user_name(token) == "alice@example.org"
        assert oidc.user_name(token) == "alice@example.org"
        assert idp.calls["userinfo"] == 1  # cached

    def test_email_in_token(self, idp):
        assert oidc.user_name(idp.token(email="bob@example.org")) == "bob@example.org"
        assert idp.calls["userinfo"] == 0

    def test_sub_without_email(self, idp):
        token = idp.token()
        idp.userinfo[token] = {"sub": "sub-1"}
        assert oidc.user_name(token) == "sub-1"

    @pytest.mark.parametrize("case", ["expired", "bad signature", "unknown issuer", "HS256", "not a JWT", "userinfo mismatch"])
    def test_invalid_tokens(self, idp, case):
        if case == "expired":
            token = idp.token(exp=int(time.time()) - 3600)
        elif case == "bad signature":
            token = idp.token(key=RSAKey.generate_key(2048, parameters={"kid": "k1"}, private=True))
        elif case == "unknown issuer":
            token = idp.token(iss="https://other.test/")
        elif case == "HS256":
            # signed with a shared secret (a server must not accept it with the public keys)
            secret = OctKey.import_key(b"a-secret-of-at-least-32-bytes-long")
            token = jwt.encode({"alg": "HS256"}, {"iss": ISSUER, "sub": "x", "exp": int(time.time()) + 60}, secret)
        elif case == "not a JWT":
            token = "opaque-token"
        else:
            token = idp.token()
            idp.userinfo[token] = {"sub": "another-sub", "email": "eve@example.org"}
        with pytest.raises(oidc.OIDCError):
            oidc.user_name(token)

    def test_audience(self, idp, monkeypatch):
        monkeypatch.setattr(settings, "OIDC_IDPS", [{"title": "IAM", "url": DISCOVERY, "audience": "opus"}])
        with pytest.raises(oidc.OIDCError):
            oidc.user_name(idp.token(email="a@example.org"))  # no aud
        with pytest.raises(oidc.OIDCError):
            oidc.user_name(idp.token(email="a@example.org", aud="other"))
        assert oidc.user_name(idp.token(email="a@example.org", aud="opus")) == "a@example.org"

    def test_key_rotation_and_refresh_limit(self, idp):
        assert oidc.user_name(idp.token(email="a@example.org")) == "a@example.org"
        # the Identity Provider uses a new key: the keys are refreshed once
        oidc._providers[ISSUER]["time"] -= oidc.REFRESH_MIN
        idp.key = RSAKey.generate_key(2048, parameters={"kid": "k2"}, private=True)
        assert oidc.user_name(idp.token(email="a@example.org")) == "a@example.org"
        jwks_calls = idp.calls["jwks"]
        # forged tokens do not trigger new requests to the Identity Provider
        forged = RSAKey.generate_key(2048, parameters={"kid": "k3"}, private=True)
        for _ in range(5):
            with pytest.raises(oidc.OIDCError):
                oidc.user_name(idp.token(key=forged, email="a@example.org"))
        assert idp.calls["jwks"] == jwks_calls


class TestBearerRequests:
    """Requests to the server with an access token and the OPUS token of the account"""

    url = settings.UWS_SERVER_ENDPOINT + "/test_"

    def test_bearer(self, idp):
        token = idp.token(email="carol@example.org")
        headers = {"Authorization": f"Bearer {token}", "X-Opus-Token": "carol-opus-token"}
        test_app.get(self.url, headers=headers, status=200)
        job_storage = getattr(uws_server.storage, settings.STORAGE + "JobStorage")()
        assert job_storage.get_users(name="carol@example.org", token="carol-opus-token")

    def test_bearer_without_opus_token(self, idp):
        response = test_app.get(self.url, headers={"Authorization": f"Bearer {idp.token()}"}, status=401)
        assert "X-Opus-Token" in response.text

    def test_invalid_bearer(self, idp):
        headers = {"Authorization": "Bearer opaque-token", "X-Opus-Token": "t"}
        response = test_app.get(self.url, headers=headers, status=401)
        assert response.headers["WWW-Authenticate"].startswith("Bearer")

    def test_basic_still_accepted(self, idp):
        auth = base64.b64encode(b"script@example.org:script-token").decode()
        test_app.get(self.url, headers={"Authorization": f"Basic {auth}"}, status=200)
