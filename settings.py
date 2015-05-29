#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Apr 29 2015
@author: mservillat
"""

DEBUG = True

LOG_FILE = 'uws_server.log'

UPLOAD_PATH = 'upload/'

PARAMS_PATH = '/home/mservillat/CTA/svn_voparis-cta/uws_server/params/'

WADL_PATH = '/home/mservillat/CTA/svn_voparis-cta/uws_server/wadl/'

# Those servers have access to /job_event/<jobid_manager> to change the phase or report an error
JOB_SERVERS = {
    '127.0.0.1': 'localhost',
    '145.238.151.10': 'tycho.obspm.fr',
}

# Define a Manager and its properties
MANAGER = 'SLURMManager'
SLURM_URL = 'tycho.obspm.fr'
SLURM_USER = 'vouws'
SLURM_USER_MAIL = 'mathieu.servillat@obspm.fr'
SLURM_PBS_PATH = '/home/mservillat/CTA/svn_voparis-cta/uws_server/pbs/'

# Maximum or default destruction interval
DESTRUCTION_INTERVAL = 30  # in days

# Maximum or default wait time (UWS1.1)
WAIT_TIME = 60  # in seconds
