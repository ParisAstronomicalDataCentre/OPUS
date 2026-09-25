#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS client

Configurable settings are defined in opus_config/client.py, and read from environment
variables prefixed with OPUS_ and from the .env file (see .env.dist). They are available
in the `settings` object (e.g. settings.BASE_URL).

This module also defines the Flask-Security configuration and the logger.
"""

import datetime
import logging
import logging.config
import os

import bleach

from opus_config import APP_PATH, ClientSettings  # noqa: F401 (APP_PATH is imported from here)

settings = ClientSettings()

# Editable configuration keywords (can be modified from the preference web page by the
# admin only), stored in CONFIG_FILE and override the settings
EDITABLE_CONFIG = [
    "UWS_SERVER_URL",
    "UWS_SERVER_ENDPOINT",
    "UWS_AUTH",
]


### Flask-Security configuration


def uia_username_mapper(identity):
    # we allow pretty much anything - but we bleach it.
    return bleach.clean(identity, strip=True)


PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=1)

SQLALCHEMY_TRACK_MODIFICATIONS = True
SECURITY_BLUEPRINT_NAME = "security"
SECURITY_FLASH_MESSAGES = True
SECURITY_USER_IDENTITY_ATTRIBUTES = [
    {"email": {"mapper": uia_username_mapper, "case_insensitive": True}},
]
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGEABLE = True
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = True


### Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s %(funcName)s: %(message)s"},
    },
    "handlers": {
        "file_client": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": settings.LOG_PATH + "/client" + settings.LOG_FILE_SUFFIX + ".log",
            "formatter": "default",
        },
        "file_client_debug": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": settings.LOG_PATH + "/client" + settings.LOG_FILE_SUFFIX + "_debug.log",
            "formatter": "default",
        },
    },
    "loggers": {
        "uws_client": {
            "level": "DEBUG",
            "handlers": ["file_client", "file_client_debug"],
        },
        "wsgiproxy": {
            "level": "DEBUG",
            "handlers": ["file_client_debug"],
        },
        "flask_admin": {
            "level": "DEBUG",
            "handlers": ["file_client_debug"],
        },
        "passlib": {
            "level": "DEBUG",
            "handlers": ["file_client_debug"],
        },
    },
}

# Set path to uws_client templates
# TEMPLATE_PATH.insert(0, app.config['APP_PATH'] + '/uws_client/templates/')

# Create dirs if they do not exist yet
for p in [settings.VAR_PATH, settings.VAR_PATH + "/logs", settings.VAR_PATH + "/config", settings.VAR_PATH + "/db"]:
    if not os.path.isdir(p):
        os.makedirs(p)

# Set logger (need existing /logs in VAR_PATH)
logging.config.dictConfig(LOGGING)
logger = logging.getLogger("uws_client")
logger.debug("Load flask client")
