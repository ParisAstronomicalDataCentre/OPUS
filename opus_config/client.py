#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS client (see base.py for how values are read)
"""

from pydantic import Field, SecretStr, computed_field, model_validator

from .base import CommonSettings


class ClientSettings(CommonSettings):
    """Settings of the UWS client"""

    # UWS server used by the client, can be any other OPUS UWS Server
    UWS_SERVER_URL: str | None = None  # Default: BASE_URL
    UWS_AUTH: str = "Basic"

    # Customize the client
    CLIENT_TITLE: str = "OPUS"
    HOME_CONTENT: str = ""

    # Users created at first start (passwords to be changed after install)
    TESTUSER_NAME: str = "testuser"
    ADMIN_DEFAULT_PW: SecretStr = SecretStr("TBD")
    TESTUSER_DEFAULT_PW: SecretStr = SecretStr("TBD")

    # Required secrets (no default), e.g. generated with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    # Key used by Flask to sign the session cookies (changing it logs out all users)
    SECRET_KEY: SecretStr = Field(min_length=16)
    # Salt used by Flask-Security to hash passwords
    # WARNING: changing it invalidates all the existing passwords of the client users
    SECURITY_PASSWORD_SALT: SecretStr = Field(min_length=1)

    # Flask-Security
    SECURITY_URL_PREFIX: str = "/accounts"
    # Users can create their own account on the registration page (<client>/accounts/register)
    SECURITY_REGISTERABLE: bool = False

    # Flask-Mail
    MAIL_USE_SSL: bool = False
    MAIL_USE_TLS: bool = False

    @model_validator(mode="after")
    def set_defaults_from_other_settings(self):
        if self.UWS_SERVER_URL is None:
            self.UWS_SERVER_URL = self.BASE_URL
        return self

    ### Values derived from other settings

    @computed_field
    @property
    def UWS_SERVER_URL_JS(self) -> str:
        # Called from javascript, set to local url (proxy) to avoid cross-calls, will connect to UWS_SERVER_URL
        return self.UWS_CLIENT_ENDPOINT + "/proxy"

    @computed_field
    @property
    def LOG_PATH(self) -> str:
        # the logs dir has to be writable from the app
        return self.VAR_PATH + "/logs"

    @computed_field
    @property
    def CONFIG_FILE(self) -> str:
        # the config dir has to be writable from the app
        return self.VAR_PATH + "/config/uws_client_config.yaml"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"sqlite:///{self.VAR_PATH}/db/flask_login.db"

    @computed_field
    @property
    def SECURITY_POST_LOGIN_VIEW(self) -> str:
        return self.UWS_CLIENT_ENDPOINT

    @computed_field
    @property
    def SECURITY_POST_LOGOUT_VIEW(self) -> str:
        return self.UWS_CLIENT_ENDPOINT + self.SECURITY_URL_PREFIX + "/login"

    @computed_field
    @property
    def SECURITY_EMAIL_SENDER(self) -> str:
        return self.SENDER_EMAIL
