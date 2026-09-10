
# OPUS global config

BASE_URL = 'http://opus-docker.localhost/opus_server'
BASE_IP = '127.0.0.1'
UWS_CLIENT_ENDPOINT = 'http://opus-docker.localhost/opus_client'  # Recommended with opus_server (i.e. relative from BASE_URL)
ADMIN_EMAIL = 'mathieu.servillat@obspm.fr'
ADMIN_NAME = 'opus-admin'
MAIL_SERVER = 'smtp-int-m.obspm.fr'
MAIL_PORT = 25
SENDER_EMAIL = 'no_reply@obspm.fr'

VAR_PATH = 'var'  # '/var/opt/opus'

# Server global config

ADMIN_TOKEN = 'e85d2a4e-27ea-5202-8b5c-241e82f5871a'
JOB_EVENT_TOKEN = 'c18de332'  # TOKEN for special user job_event, used internally
MAINTENANCE_TOKEN = '419cb761'  # TOKEN for special user maintenance, used internally
# Access rules
ALLOW_ANONYMOUS = True
CHECK_PERMISSIONS = False  # check rights to run/edit a job
CHECK_OWNER = False  # only owner can access their files

# Client global config

ADMIN_DEFAULT_PW = 'OPUS4dm1n'
TESTUSER_DEFAULT_PW = 'OPUSu53r'

#CLIENT_TITLE = "Local OPUS"
#HOME_CONTENT = "<h3>OPUS local instance</h3><p>This is my personal version from the DEV code directly</p>"

CLIENT_TITLE = "OPUS CTA"

# More config

STORAGE_TYPE = 'PostgreSQL'
PGSQL_HOST = 'db'
