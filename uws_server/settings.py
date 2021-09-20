#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS server
"""

import os
import sys
import datetime as dt
import uuid
import logging
import logging.config


### General settings

# Set debug mode, HTTP 500 Errors include traceback
DEBUG = False

# Where is located the code of the web app
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
# '/home/mservillat/CTA/git_voparis/uws_server'
# Where is located the data used/generated by the web app - has to be writable for the web server (www, _www, apache...)
VAR_PATH = '/var/opt/opus'

# URL an IP of the web server
BASE_URL = 'http://localhost/opus_server'
BASE_IP = '127.0.0.1'
LOCAL_USER = 'www'  # Appache user (may be www, _www, apache...)

# Mail server
MAIL_SERVER = 'smtp-int-m.obspm.fr'
MAIL_PORT = 25
SENDER_EMAIL = 'no_reply@obspm.fr'

### Security settings

# Admin name+token has access to user database changes (i.e. set permissions)
ADMIN_NAME = 'opus-admin'
ADMIN_EMAIL = 'a@b.com'
# IMPORTANT: use random strings for the following tokens and keep them secret
ADMIN_TOKEN = 'TBD_in_settings_local.py'
JOB_EVENT_TOKEN = 'TBD_in_settings_local.py'  # TOKEN for special user job_event, used internally
MAINTENANCE_TOKEN = 'TBD_in_settings_local.py'  # TOKEN for special user maintenant, used internally

# Access rules
ALLOW_ANONYMOUS = True
CHECK_PERMISSIONS = False  # check rights to create/edit a job
CHECK_OWNER = False

# Those servers can have access to /job_event/<jobid_manager> to change the phase or report an error
# The IP can be truncated to allow to refer to a set of IPs
# TO BE PLACED and completed in settings_local.py
JOB_SERVERS = {
    '::1': 'localhost',
    '127.0.0.1': 'localhost',
    BASE_IP: 'base_ip',
}

# The server will allow db and jdl access only from trusted clients (while waiting for an auth system)
# e.g. /db/init, /jdl/validate...
# TO BE PLACED and completed in settings_local.py
TRUSTED_CLIENTS = {
    '::1':       'localhost',
    '127.0.0.1': 'localhost',
    BASE_IP: 'base_ip',
}


### Internal settings

# max active jobs per user
NJOBS_MAX = 1  # 0 for no restriction

# Default destruction interval
DESTRUCTION_INTERVAL = 30  # in days

# Maximum and default execution duration, 0 implies unlimited execution duration
EXECUTION_DURATION_DEF = 120  # in seconds
EXECUTION_DURATION_MAX = 3600  # in seconds

# Maximum wait time (UWS1.1)
WAIT_TIME_MAX = 600  # in seconds

# ARCHIVED phase (UWS1.1)
USE_ARCHIVED_PHASE = True

# Add the provenance files to the results of the jobs
GENERATE_PROV = True

# Copy back results
COPY_RESULTS = True  # copy results from Manager to UWS server Archive (may be irrelevant if Manager = Local)

# Algo for entity hash
SHA_ALGO = '1'  # 1 (default), 224, 256, 384, 512

# Identifiers will be generated with the following functions
JOB_ID_LENGTH = 6   # length of uuid identifiers from the right, max=36
def JOB_ID_GEN():
    # uuid example: ea5caa9f-0a76-42f5-a1a7-43752df755f0
    # uuid[-12:]: 43752df755f0
    # uuid[-6:]: f755f0
    return str(uuid.uuid4())[-JOB_ID_LENGTH:]

def ENTITY_ID_GEN(**kwargs):
    # kwargs contains all the known attributes of an entity
    return JOB_ID_GEN()

def TOKEN_GEN(name):
    try:
        token = uuid.uuid5(uuid.NAMESPACE_X500, APP_PATH + name)
    except:
        token = uuid.uuid4()
    return str(token)


### Archive settings

# Local: store results in the local directory RESULTS_PATH
# SLURM: specific path accessible from the SLURM work cluster / nodes (given in ARCHIVE_PATH, need also the base access URL)
# FTP: not implemented
# VOSpace: not implemented
ARCHIVE = 'Local'
ARCHIVE_PATH = ''
ARCHIVE_URL = '/store?ID={ID}'  # use {ID} for the identifier of the result, relative or full URL


### Job Description Language settings

# VOTFile: VOTable following the Provenance DM ActivityDescription class
# WADLFile: WADL file describing the web service
# WSDLFile: WSDL file describing the web service -- not implemented
JDL = 'VOTFile'

# Parameters allowed at Job creation for job control
# either the direct name of the UWS attribute, or prefixed with 'uws:'
UWS_PARAMETERS = {
    'runId': 'User specific label for the job',  # this parameter will appear first in the form, helpful for a user to
    # find their jobs
    'executionDuration': 'Required execution duration in seconds',
    # 'uws_executionDuration': 'Required execution duration in seconds',
    'destruction': 'Date of desctruction of the job',
    #'uws_destruction': 'Date of desctruction of the job',
    'uws_quote': 'Estimation of the duration of the job',
}
UWS_PARAMETERS_KEYS = [
    'runId',
    'executionDuration',
    # 'uws_executionDuration',
    'destruction',
    # 'uws_destruction',
    'uws_quote',
]

# Control parameters allowed in a form for job creation - may be extended further below
CONTROL_PARAMETERS = UWS_PARAMETERS
# Order for the control parameters
CONTROL_PARAMETERS_KEYS = UWS_PARAMETERS_KEYS


### Storage settings

# SQLAlchemy: SQLAlchemy interface to the relational DB, e.g. SQLite, PostgreSQL...)
STORAGE = 'SQLAlchemy'
# SQLite:
# PostgreSQL:
STORAGE_TYPE = 'SQLite'
# SQLALCHEMY_DB = ''  # defined automatically further below
# SQLite storage type info
SQLITE_FILE_NAME = 'job_database.db'
# PostgreSQL storage type info
PGSQL_HOST = 'localhost'
PGSQL_PORT = 5432
PGSQL_DATABASE = 'opus'
PGSQL_USER = 'opus'
PGSQL_PASSWORD = 'opus'


### Manager settings

# Local: execution on the UWS server directly using Bash commands
# SLURM: execution through a SLURM control manager (additional config required below)
MANAGER = 'Local'
LOCAL_WORKDIR_PATH = '/tmp'


#### SLURM Manager settings

SLURM_URL = 'tycho.obspm.fr'  # 'quadri12.obspm.fr'  #
SLURM_USER = 'vouws'  # need to add the web server ssh key (e.g. user www) in .ssh/authorized_hosts
SLURM_MAIL_USER = ADMIN_EMAIL
SLURM_SCRIPTS_PATH = '/obs/vouws/scripts'
SLURM_JOBDATA_PATH = '/poubelle/vouws/jobdata'
SLURM_UPLOADS_PATH = '/poubelle/vouws/uploads'
SLURM_WORKDIR_PATH = '/scratch/vouws/workdir'
SLURM_RESULTS_PATH = '/poubelle/vouws/results'
SLURM_SBATCH_DEFAULT = {
    'nodes': 1,
    'ntasks-per-node': 1,
    'partition': 'short',  # for tycho...
    # 'partition': 'def',  # for quadri12...'
    # 'account': 'obspm',  # for quadri12...
    'mem': '200mb',
    #'tmp': '200mb',
}

PHASE_CONVERT = {
    # Conversions for SLURM job state codes
    'RUNNING': dict(phase='EXECUTING', msg='Job currently has an allocation'),
    'PENDING': dict(phase='QUEUED', msg='Job is awaiting resource allocation'),
    'CONFIGURING': dict(phase='QUEUED', msg='Job has been allocated resources, but are waiting for them '
                                            'to become ready for use'),
    'FAILED': dict(phase='ERROR', msg='Job terminated with non-zero exit code or other failure condition'),
    'NODE_FAIL': dict(phase='ERROR', msg='Job terminated due to failure of one or more allocated nodes'),
    'TIMEOUT': dict(phase='ERROR', msg='Job terminated upon reaching its time limit'),
    'PREEMPTED': dict(phase='ERROR', msg='Job terminated due to preemption'),
    'CANCELLED': dict(phase='ABORTED', msg='Job was explicitly cancelled by the user or system '
                                           'administrator. The job may or may not have been initiated'),
    'SUSPENDED': dict(phase='SUSPENDED', msg='Job has an allocation, but execution has been suspended'),
}

SLURM_PARAMETERS = {
    'slurm_mem': 'Memory to be allocated to the job',
    'slurm_nodes': 'Number of nodes allocated to the job',
    'slurm_ntasks-per-node': '',
    'slurm_partition': 'short, ...',
    'slurm_account': 'If needed (obspm for quadri12)',
}
SLURM_PARAMETERS_KEYS = [
    'slurm_mem',
    'slurm_nodes',
    'slurm_ntasks-per-node',
    'slurm_partition',
    'slurm_account',
]


# ----------
# Private variables and settings
# ----------

# UWS version (VOSI compatible)
UWS_VERSION = 'ivo://ivoa.net/std/UWS#rest-1.1'

# ISO date format for datetime
DT_FMT = '%Y-%m-%dT%H:%M:%S'

# Known phases (UWS v1.1)
PHASES = [
    'PENDING',
    # PENDING: the job is accepted by the service but not yet committed for execution by the client.
    # In this state, the job quote can be read and evaluated. This is the state into which a job enters
    # when it is first created.
    'QUEUED',
    # QUEUED: the job is committed for execution by the client but the service has not yet assigned
    # it to a processor. No Results are produced in this phase.
    'EXECUTING',
    # EXECUTING: the job has been assigned to a processor. Results may be produced at any time
    # during this phase.
    'COMPLETED',
    # COMPLETED: the execution of the job is over. The Results may be collected.
    'ERROR',
    # ERROR: the job failed to complete. No further work will be done nor Results produced. Results
    # may be unavailable or available but invalid; either way the Results should not be trusted.
    'ABORTED',
    # ABORTED: the job has been manually aborted by the user, or the system has aborted the job
    # due to lack of or overuse of resources.
    'UNKNOWN',
    # UNKNOWN: The job is in an unknown state.
    'HELD',
    # HELD: The job is HELD pending execution and will not automatically be executed (cf,
    # PENDING)
    'SUSPENDED',
    # SUSPENDED: The job has been suspended by the system during execution. This might be
    # because of temporary lack of resource. The UWS will automatically resume the job into the
    # EXECUTING phase without any intervention when resource becomes available.
    'ARCHIVED',
    # ARCHIVED: At destruction time the results associated with a job have been deleted to free up
    # resource, but the metadata associated with the job have been retained. This is an alternative
    # that the server may choose in contrast to completely destroying all record of the job to allow a
    # longer historical record of the existence of the job to be kept that would otherwise be the case
    # if limited result storage resources forces destruction.
]

# Active phases (evolution expected for job)
ACTIVE_PHASES = [
    'QUEUED',
    # 'SUSPENDED',
    'EXECUTING',
]

# Terminal phases (no evolution expected for job)
TERMINAL_PHASES = [
    'COMPLETED',
    'ERROR',
    'ABORTED',
    'HELD',
    'ARCHIVED',
]

# Table columns defined in database
JOB_ATTRIBUTES = [
    'jobid',
    'jobname',
    'run_id',
    'owner',
    'owner_token',
    'phase',
    'creation_time',
    'start_time',
    'end_time',
    'destruction_time',
    'execution_duration',
    'quote',
    'error',
    'process_id',
]
JOB_PARAMETERS_ATTR = [
    'jobid',
    'name',
    'value',
    'byref',
]
JOB_RESULTS_ATTR = [
    'jobid',
    'name',
    'url',
    'content_type'
]

# suffix to the log file (may be set by unittest_server.py or settings_local.py)
LOG_FILE_SUFFIX = ''

# ----------
# Some variables may be redefined for the local environement in a settings_local.py file
# ----------


#--- Include host-specific settings ---
if os.path.exists(APP_PATH + '/settings_local.py'):
    from settings_local import *
elif os.path.exists(APP_PATH + '/uws_server/settings_local.py'):
    from .settings_local import *
#--- Include host-specific settings ---


#--- If execution from pytest, redefine settings ---
main_dict = sys.modules['__main__'].__dict__
if 'pytest' in main_dict.get('__file__', ''):
    print('\nPerforming tests')
    now = dt.datetime.now()
    now_str = now.isoformat().split('.')[0]
    STORAGE_TYPE == 'SQLite'
    SQLITE_FILE_NAME = 'job_database_test_{}.db'.format(now_str)
    LOG_FILE_SUFFIX = '_test_' + now_str
    MANAGER = ''
    ALLOW_ANONYMOUS = True
    CHECK_PERMISSIONS = False
    CHECK_OWNER = False
#--- If execution from pytest, redefine settings ---


if MANAGER == 'SLURM':
    # Parameters allowed for SLURM sbatch header, prefixed with 'slurm:'
    CONTROL_PARAMETERS.update(SLURM_PARAMETERS)
    CONTROL_PARAMETERS_KEYS.extend(SLURM_PARAMETERS_KEYS)


#--- Set all _PATH based on APP_PATH or VAR_PATH ---
SQLITE_FILE = VAR_PATH + '/db/' + SQLITE_FILE_NAME
if STORAGE_TYPE == 'SQLite':
    # Path to sqlite db file
    SQLALCHEMY_DB = 'sqlite:///' + SQLITE_FILE
if STORAGE_TYPE == 'PostgreSQL':
    SQLALCHEMY_DB = 'postgresql://{}:{}@{}:{}/{}'.format(PGSQL_USER, PGSQL_PASSWORD, PGSQL_HOST, PGSQL_PORT, PGSQL_DATABASE)
# Logging
LOG_PATH = VAR_PATH + '/logs'
# Path for JDL files, should probably be accessed through a URL as static files
JDL_PATH = VAR_PATH + '/jdl'
# Path for script files, should probably be accessed through a URL as static files
SCRIPTS_PATH = VAR_PATH + '/jdl/scripts'
# Default path for job results and logs
JOBDATA_PATH = VAR_PATH + '/jobdata'
RESULTS_PATH = VAR_PATH + '/results'
# If POST contains files they are uploaded on the UWS server
UPLOADS_PATH = VAR_PATH + '/uploads'
# Path for e.g. SLURM sbatch files created by SLURMManager
TEMP_PATH = VAR_PATH + '/temp'
#--- Set all _PATH based on APP_PATH or VAR_PATH ---

# Create dirs if they do not exist yet
for p in [VAR_PATH + '/db', VAR_PATH + '/config',
          LOG_PATH, JDL_PATH, JOBDATA_PATH, LOCAL_WORKDIR_PATH, RESULTS_PATH, UPLOADS_PATH, TEMP_PATH,
          JDL_PATH + '/votable', JDL_PATH + '/votable/tmp', JDL_PATH + '/votable/saved',
          JDL_PATH + '/scripts', JDL_PATH + '/scripts/tmp', JDL_PATH + '/scripts/saved']:
    if not os.path.isdir(p):
        os.makedirs(p)

# Set logger
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s %(funcName)s: %(message)s'
        },
        'with_user': {
            'format': '[%(asctime)s] %(levelname)s %(funcName)s: %(message)s [%(user)s]'
        },
        'module': {
            'format': '[%(asctime)s] %(levelname)s %(module)s.%(funcName)s: %(message)s'
        },
    },
    'handlers': {
        'file_server': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/server' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'default'
        },
        'file_server_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/server' + LOG_FILE_SUFFIX + '_debug.log',
            'formatter': 'default'
        },
        'file_client': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/client' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'default'
        },
        'file_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/debug' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'module'
        },
    },
    'loggers': {
        'uws_server': {
            'level': 'DEBUG',
            'handlers': ['file_server', 'file_server_debug'],
        },
        'uws_client': {
            'level': 'DEBUG',
            'handlers': ['file_client'],
        },
        'beaker': {
            'level': 'DEBUG',
            'handlers': ['file_debug'],
        },
        'cork': {
            'level': 'DEBUG',
            'handlers': ['file_debug'],
        },
        'prov': {
            'level': 'DEBUG',
            'handlers': ['file_debug'],
        },
    }
}

# Add the username to the logs
class CustomAdapter(logging.LoggerAdapter):
    """
    This adapter expects the passed in dict-like object to have a
    'username' key, whose value in brackets is appended to the log message.
    """
    def process(self, msg, kwargs):
        return '{} [{}]'.format(msg, self.extra['username']), kwargs

# Set logger
logging.config.dictConfig(LOGGING)
logger_init = logging.getLogger('uws_server')
logger = logger_init