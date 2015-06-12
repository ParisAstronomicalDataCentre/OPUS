#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Apr 29 2015
@author: mservillat
"""

import sys

# Set debug mode, HTTP 500 Errors include traceback
DEBUG = True

LOG_FILE = 'uws_server.log'

# If parameters are files they are uploaded onthe UWS server
UPLOAD_PATH = 'upload/'

# params files are first created locally then scp to cluster
PARAMS_PATH = '/home/mservillat/CTA/git_voparis/uws-server/params/'

# path for WADL files, should probably be accessed through a URL
WADL_PATH = '/home/mservillat/CTA/git_voparis/uws-server/wadl/'

# Those servers have access to /job_event/<jobid_manager> to change the phase or report an error
JOB_SERVERS = {
    '127.0.0.1': 'localhost',
    '145.238.151.10': 'tycho.obspm.fr',
    '145.238.151.72': 'quadri12.obspm.fr',
}

# Storage of job information
STORAGE = 'SQLiteStorage'
DB_FILE = 'uws_server.db'

# Define a Manager and its properties
MANAGER = 'SLURMManager'
SLURM_URL = 'quadri12.obspm.fr'  # 'tycho.obspm.fr'
SLURM_USER = 'vouws'
SLURM_USER_MAIL = 'mathieu.servillat@obspm.fr'
SLURM_PBS_PATH = '/home/mservillat/CTA/git_voparis/uws-server/pbs/'
SLURM_SBATCH = [
    # '#SBATCH --partition=short',  # for tycho...
    '#SBATCH --account=obspm',  # for quadri12...
    '#SBATCH --partition=def',  # for quadri12...'
]

# Default destruction interval
DESTRUCTION_INTERVAL = 30  # in days

# Maximum and default execution duration, 0 implies unlimited execution duration
EXECUTION_DURATION_DEF = 120  # in seconds
EXECUTION_DURATION_MAX = 3600  # in seconds

# Maximum and default wait time (UWS1.1)
WAIT_TIME_DEF = 60  # in seconds
WAIT_TIME_MAX = 60  # in seconds

# If imported from test.py, redefine settings
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