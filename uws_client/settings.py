#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS client
"""


#----------
# WARNING:
# If ../settings_local.py is found (see settings_local.dist.py for a template),
# some variables may be redefined for the local environement at the end of
# this file.
# IMPORTANT:
# variables listed in the EDITABLE_CONFIG can be modified from the web client
# (by the admin only) and will override settings.py and ../settings_local.py.
# Values for the editable config are stored in VAR_PATH/config
#----------


import os
import bleach
import datetime
import logging
import logging.config


# ----------
# Configuration

### Application configuration

#DEBUG=False
#TESTING=False
#SERVER_NAME=  # (e.g.: 'myapp.dev:5000')
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
VAR_PATH = 'var'  # store var locally for quick test, prefer e.g. '/var/opt/opus'
UWS_CLIENT_ENDPOINT = 'http://localhost:8080'  # For local debug server with run_client.py
#UWS_CLIENT_ENDPOINT = '/opus_client'  # Recommended with server (i.e. relative from BASE_URL)
UWS_SERVER_URL_JS = UWS_CLIENT_ENDPOINT + '/proxy'  # Called from javascript, set to local url (proxy) to avoid cross-calls, will connect to UWS_SERVER_URL

### TBD in settings_local.py
BASE_URL = 'http://localhost:8082'  # For local debug server with run_server.py
UWS_SERVER_URL = None  # set to BASE_URL if None, can be any other OPUS UWS Server
UWS_SERVER_ENDPOINT = '/rest'
UWS_AUTH = 'Basic'
CLIENT_TITLE = "OPUS"
HOME_CONTENT = ""

# Editable configuration keywords (can be modified from the preference web page)
EDITABLE_CONFIG = [
    'UWS_SERVER_URL',
    'UWS_SERVER_ENDPOINT',
    'UWS_AUTH',
]

### Security configuration

ADMIN_NAME = 'opus-admin'
ADMIN_EMAIL = 'admin@opus'
TESTUSER_NAME = 'testuser'

ADMIN_TOKEN = 'TBD'   # to be defined in settings_local.py
ADMIN_DEFAULT_PW = 'TBD'   # to be changed after install, or defined in settings_local.py
TESTUSER_DEFAULT_PW = 'TBD'  # to be changed after install, or defined in settings_local.py

### OpenID Connect configuration (requires an Identity Provider, e.g. INDIGO-IAM, Google, ...)

# to be defined in settings_local.py
OIDC_IDPS = []
# OIDC_IDPS = [
#     {
#         "title": "OIDC login",  # Label for the login button
#         "description": "",  # Text shown when mouse placed on the login button
#         "url_logo": "/static/images/openid.jpg",  # Icon for the login button
#         "url": "https://<openid-server>/.well-known/openid-configuration",
#         "client_id": "",      # to be generated by Identity Provider, and defined in settings_local.py
#         "client_secret": "",  # to be generated by Identity Provider, and defined in settings_local.py
#         "scope": 'openid email profile',  # add as needed
#     },
# ]


### Flask-Security configuration


def uia_username_mapper(identity):
    # we allow pretty much anything - but we bleach it.
    return bleach.clean(identity, strip=True)


PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=1)

SQLALCHEMY_TRACK_MODIFICATIONS = True
SECURITY_BLUEPRINT_NAME = "security"
SECURITY_FLASH_MESSAGES = True
SECURITY_URL_PREFIX = '/accounts'
SECURITY_PASSWORD_SALT = 'test'
SECURITY_USER_IDENTITY_ATTRIBUTES = [
    {"email": {"mapper": uia_username_mapper, "case_insensitive": True}},
]
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGEABLE = True
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = True
MAIL_SERVER = 'smtp.'
MAIL_PORT = 25
SENDER_EMAIL = 'no_reply@opus'
MAIL_USE_SSL = False
MAIL_USE_TLS = False
# MAIL_USERNAME = ''
# MAIL_PASSWORD = ''

### Internal configuration

LOG_FILE_SUFFIX = ''

# Include host-specific setting
if os.path.exists(APP_PATH + '/settings_local.py'):
    # if __name__ == '__main__':
    from settings_local import *
    # else:
    #     from .settings_local import *
elif os.path.exists(APP_PATH + '/uws_client/settings_local.py'):
    from .settings_local import *


### Set from previous variables

if UWS_SERVER_URL is None:
    UWS_SERVER_URL = BASE_URL
UWS_SERVER_URL_JS = UWS_CLIENT_ENDPOINT + '/proxy'

if not os.path.isabs(VAR_PATH):
    VAR_PATH = os.path.join(APP_PATH, VAR_PATH)

LOG_PATH = VAR_PATH + '/logs'  # the logs dir has to be writable from the app
CONFIG_FILE = VAR_PATH + '/config/uws_client_config.yaml'  # the config dir has to be writable from the app
SQLALCHEMY_DATABASE_URI = 'sqlite:///{}/db/flask_login.db'.format(VAR_PATH)
SECURITY_POST_LOGIN_VIEW = UWS_CLIENT_ENDPOINT
SECURITY_POST_LOGOUT_VIEW = UWS_CLIENT_ENDPOINT + SECURITY_URL_PREFIX + '/login'
SECURITY_EMAIL_SENDER = SENDER_EMAIL

CONFIG_DEFAULTS = {
    'UWS_SERVER_URL': BASE_URL,
    'UWS_SERVER_ENDPOINT': '/rest',
    'UWS_AUTH': 'Basic',
}

# Set logger
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s %(funcName)s: %(message)s'
        },
    },
    'handlers': {
        'file_client': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/client' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'default'
        },
        'file_client_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/client' + LOG_FILE_SUFFIX + '_debug.log',
            'formatter': 'default'
        },
    },
    'loggers': {
        'uws_client': {
            'level': 'DEBUG',
            'handlers': ['file_client', 'file_client_debug'],
        },
        'wsgiproxy': {
            'level': 'DEBUG',
            'handlers': ['file_client_debug'],
        },
        'flask_admin': {
            'level': 'DEBUG',
            'handlers': ['file_client_debug'],
        },
        'passlib': {
            'level': 'DEBUG',
            'handlers': ['file_client_debug'],
        },
    }
}

# Set path to uws_client templates
# TEMPLATE_PATH.insert(0, app.config['APP_PATH'] + '/uws_client/templates/')

# Create dirs if they do not exist yet
for p in [VAR_PATH,
          VAR_PATH + '/logs',
          VAR_PATH + '/config',
          VAR_PATH + '/db']:
    if not os.path.isdir(p):
        os.makedirs(p)

# Set logger (need existing /logs in VAR_PATH)
logging.config.dictConfig(LOGGING)
logger = logging.getLogger('uws_client')
logger.debug('Load flask client')
