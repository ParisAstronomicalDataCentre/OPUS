
# OPUS global config

BASE_URL = 'http://localhost/opus_server'
BASE_IP = '127.0.0.1'
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

# Client global config

# IMPORTANT: keep those passwords secret
ADMIN_DEFAULT_PW = ''
TESTUSER_DEFAULT_PW = ''

CLIENT_TITLE = "OPUS"
HOME_CONTENT = "<h3>OPUS</h3><p>Observatoire de Paris UWS Server - http://opus-job-manager.readthedocs.io</p>"

# Config for PostgreSQL container (see docker-compose.yml)

STORAGE_TYPE = 'PostgreSQL'
PGSQL_HOST = 'db'

# More config (see uws_server/settings.py and uws_client/settings.py)
