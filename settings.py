#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Apr 29 2015
@author: mservillat
"""

DEBUG = True

LOG_FILE = 'uws_server.log'

DB_FILE = 'uws_server.db'

UPLOAD_PATH = 'upload/'

PARAMS_PATH = '/home/mservillat/CTA/git_voparis/uws-server/params/'

WADL_PATH = '/home/mservillat/CTA/git_voparis/uws-server/wadl/'

# Those servers have access to /job_event/<jobid_manager> to change the phase or report an error
JOB_SERVERS = {
    '127.0.0.1': 'localhost',
    '145.238.151.10': 'tycho.obspm.fr',
    '145.238.151.72': 'quadri12.obspm.fr',
}

# Define a Manager and its properties
MANAGER = 'Manager'  # 'SLURMManager'
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
