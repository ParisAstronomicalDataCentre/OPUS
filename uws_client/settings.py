#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)

import os
import bleach

# ----------
# Configuration

### Application configuration

#DEBUG=False
#TESTING=False
#SERVER_NAME=  # (e.g.: 'myapp.dev:5000')
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
VAR_PATH = '/var/opt/opus'
UWS_CLIENT_ENDPOINT = '/opus_client'
# called from javascript, set to local url (proxy) to avoid cross-calls, will connect to UWS_SERVER_URL
UWS_SERVER_URL_JS = UWS_CLIENT_ENDPOINT + '/proxy'

### to be defined in settings_local.py
BASE_URL = 'http://localhost/opus_server'
UWS_SERVER_URL = BASE_URL
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
ADMIN_EMAIL = 'a@b.com'
ADMIN_DEFAULT_PW = 'opus-admin'  # to be changed after install, or defined in settings_local.py
TESTUSER_NAME = 'testuser'
TESTUSER_DEFAULT_PW = 'testuser' # to be changed after install, or defined in settings_local.py

### Flask-Security configuration


def uia_username_mapper(identity):
    # we allow pretty much anything - but we bleach it.
    return bleach.clean(identity, strip=True)


SQLALCHEMY_TRACK_MODIFICATIONS = True
SECURITY_BLUEPRINT_NAME = "security"
SECURITY_FLASH_MESSAGES = True
SECURITY_URL_PREFIX = '/accounts'
SECURITY_FLASH_MESSAGES = False
SECURITY_PASSWORD_SALT = 'test'
SECURITY_USER_IDENTITY_ATTRIBUTES = [
    {"email": {"mapper": uia_username_mapper, "case_insensitive": True}},
]
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGEABLE = True
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = True
MAIL_SERVER = 'smtp-int-m.obspm.fr'
MAIL_PORT = 25
SENDER_EMAIL = 'no_reply@obspm.fr'
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
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/client' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'default'
        },
    },
    'loggers': {
        'uws_client': {
            'handlers': ['file_client'],
            'level': 'DEBUG',
        },
        'wsgiproxy': {
            'handlers': ['file_client'],
            'level': 'DEBUG',
        },
        'flask_admin': {
            'handlers': ['file_client'],
            'level': 'DEBUG',
        },
    }
}

# Set path to uws_client templates
# TEMPLATE_PATH.insert(0, app.config['APP_PATH'] + '/uws_client/templates/')
