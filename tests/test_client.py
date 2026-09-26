#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Unit tests for the UWS client (Flask test client), with a simulated Identity Provider, and a
UWS server running in a thread for the requests sent by the client (live_server fixture)
"""

import json
import re
import time
from urllib.parse import parse_qs, urlparse

import pytest
from flask_security import hash_password
from test_oidc import FakeIdP  # simulated Identity Provider for the server

from uws_client import uws_client as c
from uws_server import oidc as server_oidc
from uws_server.settings import settings as server_settings

IDP_NAME = "TestIdP"
PASSWORD = "local-test-password-123"
_count = [0]


def unique_email(prefix="user"):
    _count[0] += 1
    return f"{prefix}{_count[0]}.{int(time.time() * 1000)}@example.org"


def signed_in(client):
    return client.get("/accounts/profile").status_code == 200


def menu(client):
    """Name, login type and 'Change password' in the menu of the home page"""
    html = client.get("/").get_data(as_text=True)
    who = re.search(r"Signed in as <strong>([^<]*)</strong> \(([^)]*)\)", html)
    return (who.group(1), who.group(2), "Change password" in html) if who else None


def client_log():
    with open(f"{c.settings.LOG_PATH}/client{c.settings.LOG_FILE_SUFFIX}_debug.log") as f:
        return f.read()


class FakeOAuthSession:
    """Records the revocations of tokens"""

    def __init__(self, idp):
        self.idp = idp

    def revoke_token(self, url, token=None, token_type_hint=None, **kwargs):
        if self.idp.unreachable:
            raise ConnectionError("Identity Provider unreachable")
        self.idp.revoked.append((token_type_hint, token))


class ClientIdP:
    """Simulated Identity Provider for the client (the network calls of authlib are replaced)"""

    def __init__(self, monkeypatch):
        self.client = c.oauth._clients[IDP_NAME]
        self.token = None
        self.userinfo = {}
        self.metadata = {"revocation_endpoint": "https://idp.test/revoke"}
        self.revoked = []
        self.refreshed = 0
        self.unreachable = False
        monkeypatch.setattr(self.client, "authorize_access_token", lambda **kw: dict(self.token))
        monkeypatch.setattr(self.client, "userinfo", lambda **kw: dict(self.userinfo))
        monkeypatch.setattr(self.client, "load_server_metadata", self._metadata)
        monkeypatch.setattr(self.client, "_get_oauth_client", lambda **kw: FakeOAuthSession(self))
        monkeypatch.setattr(self.client, "fetch_access_token", self._refresh)

    def _metadata(self):
        if self.unreachable:
            raise ConnectionError("Identity Provider unreachable")
        return dict(self.metadata)

    def _refresh(self, grant_type=None, refresh_token=None, **kwargs):
        if self.unreachable:
            raise ConnectionError("Identity Provider unreachable")
        self.refreshed += 1
        return {"access_token": f"ACCESS-REFRESHED-{self.refreshed}", "expires_at": int(time.time()) + 300}

    def login(self, client, email=None, email_verified=True, sub=None, access_token="ACCESS-1"):
        self.token = {"access_token": access_token, "refresh_token": "REFRESH-1", "id_token": "IDTOKEN-1",
                      "token_type": "Bearer", "expires_at": int(time.time()) + 300}
        self.userinfo = {"sub": sub or f"sub-{email}"}
        if email:
            self.userinfo["email"] = email
        if email_verified is not None:
            self.userinfo["email_verified"] = email_verified
        with client.session_transaction() as s:
            s["oidc_idp"] = IDP_NAME
        return client.get("/accounts/oidc/callback")


@pytest.fixture
def idp(monkeypatch):
    return ClientIdP(monkeypatch)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(c.app.config, "WTF_CSRF_ENABLED", False)
    return c.app.test_client()


@pytest.fixture
def local_user():
    email = unique_email("local")
    with c.app.app_context():
        c.user_datastore.create_user(email=email, password=hash_password(PASSWORD), roles=["user"])
        c.db.session.commit()
    return email


def password_login(client, email):
    client.post("/accounts/login", data={"email": email, "password": PASSWORD})


def stored_token(email):
    with c.app.app_context():
        user = c.User.query.filter_by(email=email).one()
        row = c.OIDCToken.query.filter_by(user_id=user.id).first()
        return json.loads(row.token) if row else None


class TestPages:

    def test_home_signed_out(self, client):
        html = client.get("/").get_data(as_text=True)
        assert "Local login" in html
        assert html.index("Register") < html.index("Local login")  # Register at the left
        assert IDP_NAME in html  # button of the Identity Provider
        assert 'id="authenticated" style="display:none" value="false"' in html
        assert client.get("/accounts/register").status_code == 200

    def test_register_link_hidden_when_disabled(self, client, monkeypatch):
        monkeypatch.setitem(c.app.config, "SECURITY_REGISTERABLE", False)
        assert "Register" not in client.get("/").get_data(as_text=True)

    def test_roles(self):
        with c.app.app_context():
            assert sorted(r.name for r in c.Role.query.all()) == ["admin", "oidc", "user"]


class TestRegister:

    def register(self, client, email, password="register-Password-42"):
        data = {"email": email, "password": password, "password_confirm": password}
        return client.post("/accounts/register", data=data)

    def test_register(self, client, live_server):
        email = f"register{time.time_ns()}@example.org"
        response = self.register(client, email)
        assert response.status_code == 302
        with c.app.app_context():
            token = c.User.query.filter_by(email=email).one().token  # token for the UWS server
        # the user is logged in, and its account is created on the server, with its token
        assert signed_in(client)
        job_storage = getattr(__import__("uws_server.storage").storage, server_settings.STORAGE + "JobStorage")()
        assert [u["token"] for u in job_storage.get_users(name=email)] == [token]

    def test_register_username(self, client):
        """A user name that is not an email address is accepted"""
        name = f"register{time.time_ns()}"
        assert self.register(client, name).status_code == 302
        with c.app.app_context():
            assert c.User.query.filter_by(email=name).one()

    def test_register_existing(self, client):
        email = f"register{time.time_ns()}@example.org"
        self.register(client, email)
        client.get("/accounts/logout")
        response = self.register(client, email)
        assert response.status_code == 200  # form shown again, with an error
        assert "is already associated with an account" in response.get_data(as_text=True)


class TestPasswordLogin:

    def test_login_other_host_name(self, client, local_user):
        """The client is reached with another host name than UWS_CLIENT_ENDPOINT (e.g. opus-docker.localhost
        instead of localhost): the redirections after login and logout stay on this host"""
        base_url = "http://opus-docker.localhost"
        response = client.post("/accounts/login", data={"email": local_user, "password": PASSWORD}, base_url=base_url)
        assert response.status_code == 302
        assert response.headers["Location"] in ("/", f"{base_url}/")
        response = client.get("/accounts/logout", base_url=base_url)
        assert response.status_code == 302
        assert response.headers["Location"] in ("/accounts/login", f"{base_url}/accounts/login")
        # client behind nginx, with a path prefix (uvicorn --root-path /opus_client, i.e. SCRIPT_NAME)
        prefixed = f"{base_url}/opus_client"
        response = client.post("/accounts/login", data={"email": local_user, "password": PASSWORD}, base_url=prefixed)
        assert response.headers["Location"] in ("/opus_client/", f"{base_url}/opus_client/")
        response = client.get("/accounts/logout", base_url=prefixed)
        assert response.headers["Location"] in ("/opus_client/accounts/login", f"{base_url}/opus_client/accounts/login")

    def test_login_logout(self, client, local_user):
        password_login(client, local_user)
        assert signed_in(client)
        # the token is not given to the browser (pages and session cookie)
        with c.app.app_context():
            token = c.User.query.filter_by(email=local_user).one().token
        assert token not in client.get("/").get_data(as_text=True)
        with client.session_transaction() as session:
            assert "auth" not in session and token not in str(dict(session))
        assert menu(client) == (local_user, "Local", True)
        client.get("/accounts/logout")
        assert not signed_in(client)
        assert "is now logged out" in client.get("/").get_data(as_text=True)

    def test_abandoned_oidc_login(self, client, local_user):
        with client.session_transaction() as s:
            s["oidc_idp"] = IDP_NAME  # OIDC login started, then abandoned
        password_login(client, local_user)
        assert menu(client) == (local_user, "Local", True)


class TestOIDCLogin:

    def test_new_account(self, client, idp):
        email = unique_email("oidc")
        idp.login(client, email=email.upper())
        assert menu(client) == (email, IDP_NAME, False)  # no "Change password"
        with c.app.app_context():
            user = c.User.query.filter_by(email=email).one()
            assert sorted(r.name for r in user.roles) == ["oidc", "user"]
        assert stored_token(email)["refresh_token"] == "REFRESH-1"

    def test_no_email(self, client, idp):
        idp.login(client, sub="sub-without-email", email_verified=None)
        assert menu(client)[0] == "sub-without-email"

    def test_email_not_verified(self, client, idp):
        idp.login(client, email=unique_email("unverified"), email_verified=False)
        assert not signed_in(client)

    def test_local_account(self, client, idp, local_user):
        # a local account is only used if the Identity Provider verified the email
        idp.login(client, email=local_user, email_verified=None)
        assert not signed_in(client)
        idp.login(client, email=local_user, email_verified=True)
        assert menu(client) == (local_user, IDP_NAME, False)

    def test_no_secrets_in_logs(self, client, idp):
        idp.login(client, email=unique_email("secret"), access_token="SECRET-ACCESS-TOKEN")
        client.get("/accounts/profile")
        client.get("/")
        log = client_log()
        assert "SECRET-ACCESS-TOKEN" not in log and "REFRESH-1" not in log and "IDTOKEN-1" not in log


class TestOIDCLogout:

    def logout(self, client):
        response = client.get("/accounts/oidc/logout")
        return response.headers["Location"]

    def test_revocation(self, client, idp):
        email = unique_email("logout")
        idp.login(client, email=email)
        assert self.logout(client) == "/"
        assert idp.revoked == [("refresh_token", "REFRESH-1"), ("access_token", "ACCESS-1")]
        assert not signed_in(client)
        assert stored_token(email) is None

    def test_idp_unreachable(self, client, idp):
        email = unique_email("unreachable")
        idp.login(client, email=email)
        idp.unreachable = True
        assert self.logout(client) == "/"
        assert not signed_in(client)  # signed out anyway
        assert stored_token(email) is None

    def test_rp_initiated_logout(self, client, idp):
        idp.metadata["end_session_endpoint"] = "https://idp.test/logout"
        idp.login(client, email=unique_email("rp"))
        location = urlparse(self.logout(client))
        params = {k: v[0] for k, v in parse_qs(location.query).items()}
        assert location.netloc + location.path == "idp.test/logout"
        assert params == {"post_logout_redirect_uri": "http://localhost/", "client_id": "opus-test",
                          "id_token_hint": "IDTOKEN-1"}

    def test_logout_url(self, client, idp, monkeypatch):
        idps = [dict(c.settings.OIDC_IDPS[0], logout_url="https://idp.test/web-logout")]
        monkeypatch.setattr(c.settings, "OIDC_IDPS", idps)
        idp.login(client, email=unique_email("logouturl"))
        assert self.logout(client) == "https://idp.test/web-logout"


class TestServerAuth:
    """Authentication of the requests sent by the client to the server"""

    def test_basic(self, client, local_user):
        password_login(client, local_user)
        with client:
            client.get("/")
            auth, headers = c.server_auth()
        assert (auth.username, headers) == (local_user, {})

    def test_oidc(self, client, idp, monkeypatch):
        monkeypatch.setitem(c.app.config, "UWS_AUTH", "OIDC")
        email = unique_email("bearer")
        idp.login(client, email=email)
        with client:
            client.get("/")
            auth, headers = c.server_auth()
            token = c.current_user.token
        assert auth is None
        assert headers == {"Authorization": "Bearer ACCESS-1", "X-Opus-Token": token}

    def test_refresh(self, client, idp, monkeypatch):
        monkeypatch.setitem(c.app.config, "UWS_AUTH", "OIDC")
        email = unique_email("refresh")
        idp.login(client, email=email)
        with c.app.app_context():
            user = c.User.query.filter_by(email=email).one()
            row = c.OIDCToken.query.filter_by(user_id=user.id).one()
            token = json.loads(row.token)
            token["expires_at"] = int(time.time()) - 10
            row.token = json.dumps(token)
            c.db.session.commit()
        with client:
            client.get("/")
            assert c.server_auth()[1]["Authorization"] == "Bearer ACCESS-REFRESHED-1"
        assert stored_token(email)["id_token"] == "IDTOKEN-1"  # kept for the logout
        assert stored_token(email)["refresh_token"] == "REFRESH-1"

    def test_refresh_failure(self, client, idp, monkeypatch):
        monkeypatch.setitem(c.app.config, "UWS_AUTH", "OIDC")
        email = unique_email("norefresh")
        idp.login(client, email=email)
        with c.app.app_context():
            user = c.User.query.filter_by(email=email).one()
            row = c.OIDCToken.query.filter_by(user_id=user.id).one()
            token = json.loads(row.token)
            token["expires_at"] = int(time.time()) - 10
            row.token = json.dumps(token)
            c.db.session.commit()
        idp.unreachable = True
        with client:
            client.get("/")
            auth, headers = c.server_auth()
        assert auth.username == email and headers == {}  # Basic


class TestProxy:
    """Requests sent through the client to the UWS server running in a thread"""

    def test_jdl(self, client, local_user, live_server):
        password_login(client, local_user)
        response = client.get("/proxy/jdl")
        assert response.status_code == 200
        assert "jobnames" in response.get_json()

    def test_anonymous_refused(self, client, live_server, monkeypatch):
        monkeypatch.setattr(server_settings, "ALLOW_ANONYMOUS", False)
        assert client.get("/proxy/jdl").status_code == 403

    def test_secret_fields_masked_in_logs(self, client, local_user, live_server):
        password_login(client, local_user)
        client.post("/proxy/uws/test_", data={"runId": "masked", "user_token": "SECRET-FIELD-VALUE"})
        assert "SECRET-FIELD-VALUE" not in client_log()

    def test_oidc_to_server(self, client, idp, live_server, monkeypatch):
        """Client in OIDC mode: the access token (JWT) is validated by the server"""
        server_idp = FakeIdP()
        monkeypatch.setattr(server_oidc.requests, "get", server_idp.get)
        monkeypatch.setattr(server_settings, "OIDC_IDPS", [{"title": "IAM", "url": "https://iam.test/.well-known/openid-configuration"}])
        server_oidc._providers.clear()
        server_oidc._userinfo.clear()
        monkeypatch.setitem(c.app.config, "UWS_AUTH", "OIDC")
        email = unique_email("e2e")
        idp.login(client, email=email, access_token=server_idp.token(email=email))
        response = client.post("/proxy/uws/test_", data={"runId": "via-oidc"})
        assert response.status_code == 200
        with c.app.app_context():
            opus_token = c.User.query.filter_by(email=email).one().token
        job_storage = getattr(__import__("uws_server.storage").storage, server_settings.STORAGE + "JobStorage")()
        assert job_storage.get_users(name=email, token=opus_token)
        assert "(200, OIDC)" in client_log()


class TestAdminPages:

    def test_client_accounts(self, client, local_user):
        client.post("/accounts/login", data={"email": c.settings.ADMIN_NAME,
                                             "password": c.settings.ADMIN_DEFAULT_PW.get_secret_value()})
        users = client.get("/admin/user/", query_string={"search": local_user})  # 20 accounts per page
        assert users.status_code == 200 and local_user in users.get_data(as_text=True)
        assert client.get("/admin/role/").status_code == 200

    def test_client_accounts_refused(self, client, local_user):
        password_login(client, local_user)  # not an administrator
        assert client.get("/admin/user/").status_code in (302, 403)

    def admin_login(self, client):
        client.post("/accounts/login", data={"email": c.settings.ADMIN_NAME,
                                             "password": c.settings.ADMIN_DEFAULT_PW.get_secret_value()})

    def test_log_viewer(self, client, live_server):
        self.admin_login(client)
        # one page for all the log files: server and nginx (through the proxy), client
        html = client.get("/admin/logs").get_data(as_text=True)
        options = re.findall(r'<option value="(\w+)" data-url="([^"]+)"', html)
        server = [f for f, url in options if url == "http://localhost/proxy/log"]
        assert server == ["server", "server_debug", "debug", "nginx_access", "nginx_error"]
        assert [f for f, url in options if url == "/admin/client_log/text"] == ["client", "client_debug"]
        assert '<option value="client_debug" data-url="/admin/client_log/text" selected>' in client.get(
            "/admin/logs?file=client_debug").get_data(as_text=True)
        # previous pages
        assert client.get("/admin/server_log").headers["Location"] == "/admin/logs?file=server"
        assert client.get("/admin/client_log").headers["Location"] == "/admin/logs?file=client"
        # client log
        response = client.get("/admin/client_log/text", query_string={"FILE": "client_debug", "LINES": 5})
        assert response.status_code == 200 and response.mimetype == "text/plain"
        assert 0 < len(response.get_data(as_text=True).splitlines()) <= 5
        assert client.get("/admin/client_log/text", query_string={"FILE": "../x"}).status_code == 400
        # server log, through the proxy (as the log viewer)
        response = client.get("/proxy/log", query_string={"FILE": "server", "LINES": 20})
        assert response.status_code == 200
        assert len(response.get_data(as_text=True).splitlines()) <= 20

    def test_server_accounts_delete(self, client, live_server):
        """Server Accounts page: an account is deleted with its token (through the proxy)"""
        from uws_server import storage as server_storage
        job_storage = getattr(server_storage, server_settings.STORAGE + "JobStorage")()
        name = unique_email("server")
        for token in ["token-a", "token-b"]:
            job_storage.add_user(name, token=token)
        self.admin_login(client)
        assert client.delete(f"/proxy/scim/Users/{name}").status_code == 409  # 2 accounts with this name
        assert client.delete(f"/proxy/scim/Users/{name}", query_string={"token": "token-a"}).status_code == 200
        assert [u["token"] for u in job_storage.get_users(name=name)] == ["token-b"]

    def test_log_viewer_refused(self, client, local_user, live_server):
        password_login(client, local_user)  # not an administrator
        for url in ["/admin/logs", "/admin/client_log/text"]:
            assert client.get(url).status_code in (302, 403)
        assert client.get("/proxy/log").status_code == 403  # refused by the server


class TestPreferences:

    def test_defaults_and_saved_values(self, monkeypatch):
        with c.app.test_request_context():
            admin = c.user_datastore.find_user(email=c.settings.ADMIN_NAME)
            c.login_user(admin)
            view = c.preferences
            while hasattr(view, "__wrapped__"):
                view = view.__wrapped__
            html = view()
        assert f"Default: {c.settings.UWS_SERVER_URL}" in html
        # only the values that differ from the settings are saved
        monkeypatch.setitem(c.app.config, "UWS_AUTH", "OIDC")
        c.save_config()
        with open(c.settings.CONFIG_FILE) as f:
            assert f.read().strip() == "UWS_AUTH: OIDC"
        monkeypatch.setitem(c.app.config, "UWS_AUTH", c.SETTINGS_CONFIG["UWS_AUTH"])
        c.save_config()
        with open(c.settings.CONFIG_FILE) as f:
            assert f.read().strip() == "{}"
