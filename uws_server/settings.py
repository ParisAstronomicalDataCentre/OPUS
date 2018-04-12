#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS server
"""

import os
import sys
import uuid
import logging
import logging.config

# Set debug mode, HTTP 500 Errors include traceback
DEBUG = True

# Where is located the code of the web app
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
# '/home/mservillat/CTA/git_voparis/uws_server'

# Where is located the data used/generated by the web app
VAR_PATH = '/var/www/opus'
# This is used to defined the following structure:
# /db/' + SQLITE_FILE_NAME
# /logs'
# /jdl'
# /jdl/scripts'
# /jobdata'
# /uploads'
# /temp'

# suffix to the log file (may be set by test.py of settings_local.py)
LOG_FILE_SUFFIX = ''

# URL an IP of the web server
BASE_URL = 'http://localhost'
BASE_IP = '127.0.0.1'

# Admin name+pid has access to user database changes (i.e. set permissions)
ADMIN_NAME = 'admin'
ADMIN_PID = 'e85d2a4e-27ea-5202-8b5c-241e82f5871a'
ADMIN_EMAIL = 'mathieu.servillat@obspm.fr'
JOB_EVENT_PID = 'c18de332'  # PID for special user job_event, used internally
MAINTENANCE_PID = '419cb761'  # PID for special user maintenant, used internally
ALLOW_ANONYMOUS = True
CHECK_PERMISSIONS = True

# Identifiers will be generated with the following UUID_GEN function
UUID_LENGTH = 6   # length of uuid identifiers from the right, max=36
def UUID_GEN():
    # uuid example: ea5caa9f-0a76-42f5-a1a7-43752df755f0
    # uuid[-12:]: 43752df755f0
    # uuid[-6:]: f755f0
    return str(uuid.uuid4())[-UUID_LENGTH:]

# Those servers can have access to /job_event/<jobid_manager> to change the phase or report an error
# The IP can be truncated to allow to refer to a set of IPs
JOB_SERVERS = {
    '::1': 'localhost',
    '127.0.0.1': 'localhost',
    '145.238.151.': 'tycho/quadri12',
}

# The server will allow db and jdl access only from trusted clients (while waiting for an auth system)
# e.g. /db/init, /jdl/validate...
TRUSTED_CLIENTS = {
    '::1':             'localhost',
    '127.0.0.1':       'localhost',
    '145.238.193.69':  'voparis-uws-test.obspm.fr',
    '145.238.168.3':   'savagnin_ucopia',
    '145.238.180.240': 'savagnin_cable',
    '93.15.50.214':    'savagnin_home',
}

# Job Description Language files
# VOTFile: VOTable following the Provenance DM ActivityDescription class
# WADLFile: WADL file describing the web service
# WSDLFile: WSDL file describing the web service -- not implemented
JDL = 'VOTFile'

# Storage of job information (SQLAlchemy, SQLite, PGSQL)
# SQLAlchemy: SQLAlchemy interface to the relational DB, e.g. SQLite, PostgreSQL...)
# SQLite: direct use of SQLite -- to be deprecated
STORAGE = 'SQLAlchemy'
# SQLALCHEMY_DB = ''  # defined further below
# SQLite storage info
SQLITE_FILE_NAME = 'job_database.db'
# PGSQL storage info
PGSQL_HOST = 'localhost'
PGSQL_PORT = 5432
PGSQL_DATABASE = 'opus'
PGSQL_USER = 'opus'
PGSQL_PASSWORD = 'opus'

# Archive for results
# Local: store results in the local directory VAR_PATH/archive or specific path on the UWS server (if given in ARCHIVE_PATH)
# SLURM: specific path accessible from the SLURM work cluster / nodes (given in ARCHIVE_PATH, need also the base access URL)
# FTP: not implemented
# VOSpace: not implemented
ARCHIVE = 'Local'
ARCHIVE_PATH = ''
ARCHIVE_URL = ''

# Copy back results
COPY_RESULTS = True  # copy results from Manager to UWS server (may be irrelevant if Manager = Local)
# Add the provenance files to the results of the jobs
GENERATE_PROV = True

# Define a Manager and its properties
# Local: execution on the UWS server directly using Bash commands
# SLURM: execution through a SLURM control manager (additional config required)
MANAGER = 'Local'
LOCAL_WORKDIR_PATH = '/tmp'
# SLURM Manager
SLURM_URL = 'tycho.obspm.fr'  # 'quadri12.obspm.fr'  #
SLURM_USER = 'vouws'  # need to add the web server ssh key (e.g. user www) in .ssh/authorized_hosts
SLURM_MAIL_USER = ADMIN_EMAIL
SLURM_SCRIPTS_PATH = '/obs/vouws/scripts'
SLURM_WORKDIR_PATH = '/scratch/vouws'
SLURM_JOBDATA_PATH = '/poubelle/vouws/jobdata'
SLURM_RESULTS_PATH = '/poubelle/vouws/results'
SLURM_SBATCH_DEFAULT = {
    'mem': '200mb',
    'nodes': 1,
    'ntasks-per-node': 1,
    'partition': 'short',  # for tycho...
    # 'account': 'obspm',  # for quadri12...
    # 'partition': 'def',  # for quadri12...'
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

# Parameters allowed at Job creation for job control
JOB_CONTROL_PARAMETERS = [
    'uws:execution_duration',
    'uws:quote',
    'slurm:mem',
    'slurm:nodes',
    'slurm:ntasks-per-node',
    'slurm:partition',
    'slurm:account',
]

# Default destruction interval
DESTRUCTION_INTERVAL = 30  # in days

# Maximum and default execution duration, 0 implies unlimited execution duration
EXECUTION_DURATION_DEF = 120  # in seconds
EXECUTION_DURATION_MAX = 3600  # in seconds

# Maximum wait time (UWS1.1)
WAIT_TIME_MAX = 600  # in seconds

# ARCHIVED phase (UWS1.1)
USE_ARCHIVED_PHASE = True


# ----------
# Internal variables
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
    'PENDING',
    'QUEUED',
    'EXECUTING',
]

# Terminal phases (no evolution expected for job)
TERMINAL_PHASES = [
    'COMPLETED',
    'ERROR',
    'ABORTED',
    'HELD',
    # 'SUSPENDED',
    'ARCHIVED',
]

# Table columns defined in database
JOB_ATTRIBUTES = [
    'jobid',
    'jobname',
    'run_id',
    'phase',
    'creation_time',
    'start_time',
    'end_time',
    'destruction_time',
    'execution_duration',
    'quote',
    'error',
    'owner',
    'owner_pid',
    'pid',
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


# ----------
# Some variables may be redefined for the local environement in a settings_local.py file
# ----------


#--- Include host-specific settings ------------------------------------------------------------------------------------
if os.path.exists(APP_PATH + '/uws_server/settings_local.py'):
    from settings_local import *
#--- Include host-specific settings ------------------------------------------------------------------------------------


#--- If imported from test.py, redefine settings -----------------------------------------------------------------------
main_dict = sys.modules['__main__'].__dict__
if 'test.py' in main_dict.get('__file__', ''):
    print('\nPerforming tests')
    if 'LOG_FILE_SUFFIX' in main_dict:
        LOG_FILE_SUFFIX = main_dict['LOG_FILE_SUFFIX']
    if 'STORAGE' in main_dict:
        STORAGE = main_dict['STORAGE']
    if 'SQLITE_FILE_NAME' in main_dict:
        SQLITE_FILE_NAME = main_dict['SQLITE_FILE_NAME']
    if 'MANAGER' in main_dict:
        MANAGER = main_dict['MANAGER']
#--- If imported from test.py, redefine settings -----------------------------------------------------------------------


#--- Set all _PATH based on APP_PATH or VAR_PATH -----------------------------------------------------------------------
# Path to sqlite db file
SQLITE_FILE = VAR_PATH + '/db/' + SQLITE_FILE_NAME
SQLALCHEMY_DB = 'sqlite:///' + SQLITE_FILE
# SQLALCHEMY_DB = 'postgresql://user:pwd@localhost:5432/mydatabase'
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
UPLOAD_PATH = VAR_PATH + '/uploads'
# Path for e.g. SLURM sbatch files created by SLURMManager
TEMP_PATH = VAR_PATH + '/temp'
#--- Set all _PATH based on APP_PATH or VAR_PATH -----------------------------------------------------------------------


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