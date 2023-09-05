
# OPUS global config

# For local debug servers
BASE_URL = 'http://localhost:8082'
UWS_CLIENT_ENDPOINT = 'http://localhost:8080'
BASE_IP = '127.0.0.1'
# For web servers, e.g. Apache2
#BASE_URL = 'http://localhost/opus_server'
#UWS_CLIENT_ENDPOINT = '/opus_client'  # Recommended with opus_server (i.e. relative from BASE_URL)
#BASE_IP = '127.0.0.1'

ADMIN_EMAIL = ''
ADMIN_NAME = 'opus-admin'
MAIL_SERVER = 'smtp.'
MAIL_PORT = 25
SENDER_EMAIL = ''  # e.g. no_reply@example.com
# Directory where app data is stored - has to be writable for the web server (www, _www, apache...)
VAR_PATH = '/var/opt/opus'

# Server global config

# IMPORTANT: use random strings for the following tokens and keep them secret
ADMIN_TOKEN = ''  # TOKEN of admin user
JOB_EVENT_TOKEN = ''  # TOKEN for special user job_event, used internally
MAINTENANCE_TOKEN = ''  # TOKEN for special user maintenance, used internally
# Access rules
ALLOW_ANONYMOUS = True
CHECK_PERMISSIONS = False  # check rights to run/edit a job
CHECK_OWNER = False  # only owner can access their files
# job servers can have access to /job_event/<jobid_manager> to change the phase or report an error
# The IP can be truncated to allow to refer to a set of IPs (e.g. '127.' for 127.*.*.*)
JOB_SERVERS = {
    '::1': 'localhost',
    '127.0.0.1': 'localhost',
    BASE_IP: 'base_ip',
}
# trusted clients can have access to /db and /jdl (while waiting for an A&A system)
# e.g. /db/init, /jdl/validate...
TRUSTED_CLIENTS = {
    '::1':       'localhost',
    '127.0.0.1': 'localhost',
    BASE_IP: 'base_ip',
}

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



# More config (see uws_server/settings.py and uws_client/settings.py)
