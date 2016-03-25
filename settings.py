#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Apr 29 2015
@author: mservillat
"""

import os
import sys
import logging

# Set debug mode, HTTP 500 Errors include traceback
DEBUG = True
LOG_FILE = 'logs/app.log'

BASE_URL = 'http://localhost:8080'

APP_PATH = '/home/mservillat/CTA/git_voparis/uws-server'

# Those servers have access to /job_event/<jobid_manager> to change the phase or report an error
JOB_SERVERS = {
    '127.0.0.1': 'localhost',
    '145.238.151.10': 'tycho.obspm.fr',
    '145.238.151.72': 'quadri12.obspm.fr',
    '145.238.151.130': 'tyctst0',
    '145.238.151.11': 'tycho',
    '145.238.151.12': 'tycho',
    '145.238.151.13': 'tycho',
    '145.238.151.14': 'tycho',
    '145.238.151.15': 'tycho',
    '145.238.151.16': 'tycho',
    '145.238.151.17': 'tycho',
    '145.238.151.18': 'tycho',
    '145.238.151.19': 'tycho',
    '145.238.151.20': 'tycho',
    '145.238.151.21': 'tycho',
    '145.238.151.22': 'tycho',
    '145.238.151.23': 'tycho',
    '145.238.151.24': 'tycho',
    '145.238.151.25': 'tycho',
    '145.238.151.26': 'tycho',
    '145.238.151.27': 'tycho',
    '145.238.151.28': 'tycho',
    '145.238.151.29': 'tycho',
}

# Storage of job information
STORAGE = 'SQLiteStorage'
DB_FILE = 'job_database.db'

# Define a Manager and its properties
MANAGER = 'SLURMManager'
SLURM_URL = 'tycho.obspm.fr'  # 'quadri12.obspm.fr'  #
SLURM_USER = 'vouws'
SLURM_USER_MAIL = 'mathieu.servillat@obspm.fr'
SLURM_HOME_PATH = '/obs/vouws'  # '/obs/vouws'
SLURM_JOBDATA_PATH = '/poubelle/vouws/jobdata'
SLURM_WORKDIR_PATH = '/scratch/vouws'
SLURM_SBATCH_ADD = [
    "#SBATCH --mem=200mb",
    "#SBATCH --nodes=1 --ntasks-per-node=1",
    '#SBATCH --partition=short',  # for tycho...
    # '#SBATCH --account=obspm',  # for quadri12...
    # '#SBATCH --partition=def',  # for quadri12...'
]
PHASE_CONVERT = {
    # Conversions for SLURM job state codes
    'RUNNING': dict(phase='EXECUTING', msg='Job currently has an allocation.'),
    'PENDING': dict(phase='QUEUED', msg='Job is awaiting resource allocation.'),
    'CONFIGURING': dict(phase='QUEUED', msg='Job has been allocated resources, but are waiting for them '
                                            'to become ready for use'),
    'FAILED': dict(phase='ERROR', msg='Job terminated with non-zero exit code or other failure condition.'),
    'NODE_FAIL': dict(phase='ERROR', msg='Job terminated due to failure of one or more allocated nodes.'),
    'TIMEOUT': dict(phase='ERROR', msg='Job terminated upon reaching its time limit.'),
    'PREEMPTED': dict(phase='ERROR', msg='Job terminated due to preemption.'),
    'CANCELLED': dict(phase='ABORTED', msg='Job was explicitly cancelled by the user or system '
                                           'administrator. The job may or may not have been initiated.'),
    'SUSPENDED': dict(phase='SUSPENDED', msg='Job has an allocation, but execution has been suspended.'),
}

# Default destruction interval
DESTRUCTION_INTERVAL = 30  # in days

# Maximum and default execution duration, 0 implies unlimited execution duration
EXECUTION_DURATION_DEF = 120  # in seconds
EXECUTION_DURATION_MAX = 3600  # in seconds

# Maximum and default wait time (UWS1.1)
WAIT_TIME_DEF = 60  # in seconds
WAIT_TIME_MAX = 60  # in seconds

# ISO date format for datetime
DT_FMT = '%Y-%m-%dT%H:%M:%S'

# Table columns defined in database
JOB_ATTRIBUTES = [
    'jobid',
    'jobname',
    'phase',
    'start_time',
    'end_time',
    'destruction_time',
    'execution_duration',
    'quote',
    'error',
    'owner',
    'owner_pid',
    'run_id',
    'jobid_cluster',
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
    'url'
]

# Known phases
PHASES = [
    'PENDING',
    'QUEUED',
    'EXECUTING',
    'COMPLETED',
    'ERROR',
    'ABORTED',
    'UNKNOWN',
    'HELD',
    'SUSPENDED',
]

# Terminal phases (no evolution expected for job)
TERMINAL_PHASES = [
    'COMPLETED',
    'ERROR',
    'ABORTED',
    'HELD',
    # 'SUSPENDED',
]

#--- Include host-specific settings ------------------------------------------------------------------------------------
if os.path.exists('settings_local.py'):
    from settings_local import *
#--- Include host-specific settings ------------------------------------------------------------------------------------

#--- If imported from test.py, redefine settings -----------------------------------------------------------------------
main_dict = sys.modules['__main__'].__dict__
if 'test.py' in main_dict.get('__file__', ''):
    print '\nPerforming tests'
    if 'LOG_FILE' in main_dict:
        LOG_FILE = main_dict['LOG_FILE']
    if 'STORAGE' in main_dict:
        STORAGE = main_dict['STORAGE']
    if 'DB_FILE' in main_dict:
        DB_FILE = main_dict['DB_FILE']
    if 'MANAGER' in main_dict:
        MANAGER = main_dict['MANAGER']
#--- If imported from test.py, redefine settings -----------------------------------------------------------------------
    
#--- Set all _PATH based on APP_PATH -----------------------------------------------------------------------------------
# If POST contains files they are uploaded on the UWS server
UPLOAD_PATH = APP_PATH + '/uploads'
# Path for job results and logs
JOBDATA_PATH = APP_PATH + '/jobdata'
# Path for job results and logs
RESULTS_PATH = JOBDATA_PATH + '/results'
# Path for WADL files, should probably be accessed through a URL as static files
WADL_PATH = APP_PATH + '/job_def/wadl'
# Path for WADL files, should probably be accessed through a URL as static files
SCRIPT_PATH = APP_PATH + '/job_def/scripts'
# Path for SLURM sbatch files created by SLURMManager
SBATCH_PATH = APP_PATH + '/sbatch'
#--- Set all _PATH based on APP_PATH -----------------------------------------------------------------------------------

# Set logger
logging.basicConfig(
    filename=LOG_FILE,
    format='[%(asctime)s] %(levelname)s %(module)s.%(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)
