#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)


#----------
# WARNING:
# This file should be copied to settings_local.py and modified to configure
# the execution of UWS server and client as desired (see "TBD" below)
# The settings_local.py file contains default passwords and internal tokens,
# it should thus be kept private (no git tacking, no public read access).
#----------


#----------
# OPUS global config

# For local debug servers
BASE_URL = 'http://localhost:8082'
UWS_CLIENT_ENDPOINT = 'http://localhost:8080'
BASE_IP = '127.0.0.1'
# For web servers, e.g. Apache2
#BASE_URL = 'http://localhost/opus_server'
#UWS_CLIENT_ENDPOINT = '/opus_client'  # Recommended with opus_server (i.e. relative from BASE_URL)
#BASE_IP = '127.0.0.1'

ADMIN_NAME = 'opus-admin'
ADMIN_EMAIL = ''
ADMIN_TOKEN = 'TBD'  # TOKEN of admin user

MAIL_SERVER = 'smtp.'
MAIL_PORT = 25
SENDER_EMAIL = 'no_reply@'  # e.g. no_reply@example.com

# Directory where app data is stored
# It has to be writable for the web server user (www, _www, apache...)
# try 'var' to store var locally for quick test
VAR_PATH = '/var/opt/opus'


#----------
# Client global config

# IMPORTANT: keep those passwords secret
ADMIN_DEFAULT_PW = 'TBD'
TESTUSER_DEFAULT_PW = 'TBD'

CLIENT_TITLE = "OPUS"
HOME_CONTENT = "<h3>OPUS</h3><p>Observatoire de Paris UWS Server - http://opus-job-manager.readthedocs.io</p>"

# Configure OIDC IdPs

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


#----------
# Server global config

# IMPORTANT: use random strings for the following tokens and keep them secret
JOB_EVENT_TOKEN = 'TBD'  # TOKEN for special user job_event, used internally
MAINTENANCE_TOKEN = 'TBD'  # TOKEN for special user maintenance, used internally

# Access rules
ALLOW_ANONYMOUS = True
CHECK_PERMISSIONS = False  # check rights to run/edit a job
CHECK_OWNER = False  # only owner can access their files

# Job servers can have access to /job_event/<jobid_manager> to change the phase or report an error
# The IP can be truncated to allow to refer to a set of IPs (e.g. '127.' for 127.*.*.*)
JOB_SERVERS = {
    '::1': 'localhost',
    '127.0.0.1': 'localhost',
    BASE_IP: 'base_ip',
}

# Trusted clients can have access to /db and /jdl
# e.g. /db/init, /jdl/validate...
TRUSTED_CLIENTS = {
    '::1':       'localhost',
    '127.0.0.1': 'localhost',
    BASE_IP: 'base_ip',
}


#----------
# More config (see uws_server/settings.py and uws_client/settings.py)
