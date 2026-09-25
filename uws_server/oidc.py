#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Validation of the OpenID Connect access tokens sent to the server (Authorization: Bearer)

The access token must be a JWT (e.g. INDIGO-IAM), signed by one of the Identity Providers
of the setting OIDC_IDPS. It is checked with the keys of the Identity Provider (JWKS, found
with its discovery URL): signature, issuer, expiration, and audience if the Identity
Provider has an "audience" in OIDC_IDPS.

The name of the user is the email given by the userinfo endpoint of the Identity Provider
(lower case), or the "sub" claim if there is no email, as for the client.
"""

import hashlib
import json
import threading
import time

import requests
from joserfc import jws, jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from .settings import logger, settings

# Asymmetric algorithms only (a symmetric algorithm would use the public key as a secret)
ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"]
HTTP_TIMEOUT = 10  # in seconds
METADATA_TTL = 3600  # in seconds, then discovery and keys are read again
USERINFO_TTL_MAX = 3600  # in seconds, and not longer than the expiration of the token
REFRESH_MIN = 60  # in seconds, minimum interval to refresh the keys of an Identity Provider


class OIDCError(Exception):
    """The access token is not valid"""

    pass


_lock = threading.Lock()
_providers = {}  # issuer -> {"idp", "metadata", "keys", "time"}
_userinfo = {}  # sha256(token) -> (name, expiration time)


def _discover(idp):
    """Metadata and keys of an Identity Provider"""
    metadata = requests.get(idp["url"], timeout=HTTP_TIMEOUT).json()
    jwks = requests.get(metadata["jwks_uri"], timeout=HTTP_TIMEOUT).json()
    return {"idp": idp, "metadata": metadata, "keys": KeySet.import_key_set(jwks), "time": time.time()}


def _provider(issuer, refresh=False):
    """Identity Provider of OIDC_IDPS with this issuer, with its metadata and keys (cached)

    Requests to the Identity Providers are limited: an unknown issuer does not trigger a new
    discovery of the Identity Providers already known, and the keys are refreshed (e.g. after
    a key rotation) at most every REFRESH_MIN seconds.
    """
    now = time.time()
    with _lock:
        provider = _providers.get(issuer)
        if provider:
            age = now - provider["time"]
            if age < METADATA_TTL and (not refresh or age < REFRESH_MIN):
                return provider
            idps = [provider["idp"]]
        else:
            known = [p["idp"] for p in _providers.values() if now - p["time"] < METADATA_TTL]
            idps = [idp for idp in settings.OIDC_IDPS if not any(idp is k for k in known)]
        for idp in idps:
            try:
                p = _discover(idp)
            except (requests.RequestException, ValueError, KeyError) as e:
                logger.warning(f"OIDC discovery failed for {idp.get('title')}: {e}")
                continue
            _providers[p["metadata"]["issuer"]] = p
            if p["metadata"]["issuer"] == issuer:
                return p
    raise OIDCError(f"Unknown issuer: {issuer}")


def _claims(access_token):
    """Validated claims of the access token"""
    try:
        issuer = json.loads(jws.extract_compact(access_token.encode()).payload)["iss"]
    except (ValueError, KeyError, JoseError) as e:
        raise OIDCError("The access token is not a JWT with an issuer") from e
    provider = _provider(issuer)
    try:
        try:
            token = jwt.decode(access_token, provider["keys"], algorithms=ALGORITHMS)
        except (JoseError, ValueError):
            # the keys of the Identity Provider may have changed
            provider = _provider(issuer, refresh=True)
            token = jwt.decode(access_token, provider["keys"], algorithms=ALGORITHMS)
        options = {"iss": {"essential": True, "value": issuer}, "exp": {"essential": True}}
        audience = provider["idp"].get("audience")
        if audience:
            options["aud"] = {"essential": True, "value": audience}
        jwt.JWTClaimsRegistry(leeway=30, **options).validate(token.claims)
    except (JoseError, ValueError) as e:
        raise OIDCError(f"Invalid access token: {e}") from e
    return token.claims, provider


def _name(access_token, claims, provider):
    """Email of the user (from the token or userinfo), or sub"""
    email = claims.get("email")
    if not email:
        key = hashlib.sha256(access_token.encode()).hexdigest()
        cached = _userinfo.get(key)
        if cached and cached[1] > time.time():
            return cached[0]
        url = provider["metadata"].get("userinfo_endpoint")
        if url:
            try:
                response = requests.get(
                    url, headers={"Authorization": f"Bearer {access_token}"}, timeout=HTTP_TIMEOUT
                )
                response.raise_for_status()
                userinfo = response.json()
            except (requests.RequestException, ValueError) as e:
                raise OIDCError(f"Cannot get userinfo: {e}") from e
            if userinfo.get("sub") != claims.get("sub"):
                raise OIDCError("userinfo does not match the access token")
            email = userinfo.get("email")
    name = email.lower() if email else claims["sub"]
    if not claims.get("email"):
        expiration = min(claims["exp"], time.time() + USERINFO_TTL_MAX)
        with _lock:
            _userinfo[key] = (name, expiration)
            for k in [k for k, v in _userinfo.items() if v[1] <= time.time()]:
                del _userinfo[k]
    return name


def user_name(access_token):
    """Name of the user for a valid access token, else raise OIDCError"""
    if not settings.OIDC_IDPS:
        raise OIDCError("No OpenID Connect Identity Provider is configured on this server")
    claims, provider = _claims(access_token)
    name = _name(access_token, claims, provider)
    # (never log the token itself)
    logger.debug(f"OIDC access token accepted for {name} (iss={claims['iss']}, sub={claims['sub']})")
    return name
