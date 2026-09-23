#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS server

Configurable settings are defined in opus_config/server.py, and read from environment
variables prefixed with OPUS_ and from the .env file (see .env.dist). They are available
in the `settings` object (e.g. settings.BASE_URL).

This module also defines the constants of the UWS protocol and of OPUS, the identifier
generators and the logger.
"""

import logging
import logging.config
import os

from opus_config import APP_PATH, ServerSettings  # noqa: F401 (APP_PATH is imported from here)

settings = ServerSettings()

# Compatibility: settings as module-level names (e.g. BASE_URL), to be replaced by
# settings.<NAME> in the modules that import them
globals().update(settings.export())


### Identifiers and tokens generators (compatibility, see settings.new_job_id()...)


def JOB_ID_GEN():
    return settings.new_job_id()


def ENTITY_ID_GEN(**kwargs):
    return settings.new_entity_id(**kwargs)


def TOKEN_GEN(context=None):
    return settings.new_token(context)


### Control parameters

# Parameters allowed at Job creation for job control
# either the direct name of the UWS attribute, or prefixed with 'uws:'
UWS_PARAMETERS = {
    "runId": "User specific label for the job",  # this parameter will appear first in the form, helpful for a user to
    # find their jobs
    "executionDuration": "Required execution duration in seconds",
    # 'uws_executionDuration': 'Required execution duration in seconds',
    "destruction": "Date of desctruction of the job",
    #'uws_destruction': 'Date of desctruction of the job',
    "uws_quote": "Estimation of the duration of the job",
}
UWS_PARAMETERS_KEYS = [
    "runId",
    "executionDuration",
    # 'uws_executionDuration',
    "destruction",
    # 'uws_destruction',
    "uws_quote",
]

# Control parameters allowed in a form for job creation - may be extended further below
CONTROL_PARAMETERS = UWS_PARAMETERS
# Order for the control parameters
CONTROL_PARAMETERS_KEYS = UWS_PARAMETERS_KEYS


### SLURM Manager constants

PHASE_CONVERT = {
    # Conversions for SLURM job state codes
    "RUNNING": {"phase": "EXECUTING", "msg": "Job currently has an allocation"},
    "PENDING": {"phase": "QUEUED", "msg": "Job is awaiting resource allocation"},
    "CONFIGURING": {
        "phase": "QUEUED",
        "msg": "Job has been allocated resources, but are waiting for them "
        "to become ready for use",
    },
    "FAILED": {
        "phase": "ERROR",
        "msg": "Job terminated with non-zero exit code or other failure condition",
    },
    "NODE_FAIL": {
        "phase": "ERROR",
        "msg": "Job terminated due to failure of one or more allocated nodes",
    },
    "TIMEOUT": {"phase": "ERROR", "msg": "Job terminated upon reaching its time limit"},
    "PREEMPTED": {"phase": "ERROR", "msg": "Job terminated due to preemption"},
    "CANCELLED": {
        "phase": "ABORTED",
        "msg": "Job was explicitly cancelled by the user or system "
        "administrator. The job may or may not have been initiated",
    },
    "SUSPENDED": {
        "phase": "SUSPENDED",
        "msg": "Job has an allocation, but execution has been suspended",
    },
}

SLURM_PARAMETERS = {
    "slurm_mem": "Memory to be allocated to the job (default: 1gb)",
    "slurm_nodes": "Number of nodes allocated to the job (default: 1)",
    "slurm_ntasks-per-node": "Number of tasks per node (default: 16)",
    "slurm_partition": "padc_medium, short, ...",
    "slurm_account": "If needed (padc_medium for tycho, obspm for quadri12, ...)",
}
SLURM_PARAMETERS_KEYS = [
    "slurm_mem",
    "slurm_nodes",
    "slurm_ntasks-per-node",
    "slurm_partition",
    "slurm_account",
]


if settings.MANAGER == "SLURM":
    # Parameters allowed for SLURM sbatch header, prefixed with 'slurm:'
    CONTROL_PARAMETERS.update(SLURM_PARAMETERS)
    CONTROL_PARAMETERS_KEYS.extend(SLURM_PARAMETERS_KEYS)


# ----------
# Private variables and settings
# ----------

# UWS version (VOSI compatible)
UWS_VERSION = "ivo://ivoa.net/std/UWS#rest-1.1"

# ISO date format for datetime
DT_FMT = "%Y-%m-%dT%H:%M:%S"

# Known phases (UWS v1.1)
PHASES = [
    "PENDING",
    # PENDING: the job is accepted by the service but not yet committed for execution by the client.
    # In this state, the job quote can be read and evaluated. This is the state into which a job enters
    # when it is first created.
    "QUEUED",
    # QUEUED: the job is committed for execution by the client but the service has not yet assigned
    # it to a processor. No Results are produced in this phase.
    "EXECUTING",
    # EXECUTING: the job has been assigned to a processor. Results may be produced at any time
    # during this phase.
    "COMPLETED",
    # COMPLETED: the execution of the job is over. The Results may be collected.
    "ERROR",
    # ERROR: the job failed to complete. No further work will be done nor Results produced. Results
    # may be unavailable or available but invalid; either way the Results should not be trusted.
    "ABORTED",
    # ABORTED: the job has been manually aborted by the user, or the system has aborted the job
    # due to lack of or overuse of resources.
    "UNKNOWN",
    # UNKNOWN: The job is in an unknown state.
    "HELD",
    # HELD: The job is HELD pending execution and will not automatically be executed (cf,
    # PENDING)
    "SUSPENDED",
    # SUSPENDED: The job has been suspended by the system during execution. This might be
    # because of temporary lack of resource. The UWS will automatically resume the job into the
    # EXECUTING phase without any intervention when resource becomes available.
    "ARCHIVED",
    # ARCHIVED: At destruction time the results associated with a job have been deleted to free up
    # resource, but the metadata associated with the job have been retained. This is an alternative
    # that the server may choose in contrast to completely destroying all record of the job to allow a
    # longer historical record of the existence of the job to be kept that would otherwise be the case
    # if limited result storage resources forces destruction.
]

# Active phases (evolution expected for job)
ACTIVE_PHASES = [
    "QUEUED",
    # 'SUSPENDED',
    "EXECUTING",
]

# Terminal phases (no evolution expected for job)
TERMINAL_PHASES = [
    "COMPLETED",
    "ERROR",
    "ABORTED",
    "HELD",
    "ARCHIVED",
]

# Table columns defined in database
JOB_ATTRIBUTES = [
    "jobid",
    "jobname",
    "run_id",
    "owner",
    "owner_token",
    "phase",
    "creation_time",
    "start_time",
    "end_time",
    "destruction_time",
    "execution_duration",
    "quote",
    "error",
    "process_id",
]
JOB_PARAMETERS_ATTR = [
    "jobid",
    "name",
    "value",
    "byref",
]
JOB_RESULTS_ATTR = ["jobid", "name", "url", "content_type"]


# Set logger
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s %(funcName)s: %(message)s"},
        "with_user": {
            "format": "[%(asctime)s] %(levelname)s %(funcName)s: %(message)s [%(user)s]"
        },
        "module": {
            "format": "[%(asctime)s] %(levelname)s %(module)s.%(funcName)s: %(message)s"
        },
    },
    "handlers": {
        "file_server": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": settings.LOG_PATH + "/server" + settings.LOG_FILE_SUFFIX + ".log",
            "formatter": "default",
        },
        "file_server_debug": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": settings.LOG_PATH + "/server" + settings.LOG_FILE_SUFFIX + "_debug.log",
            "formatter": "default",
        },
        "file_debug": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": settings.LOG_PATH + "/debug" + settings.LOG_FILE_SUFFIX + ".log",
            "formatter": "module",
        },
    },
    "loggers": {
        "uws_server": {
            "level": "DEBUG",
            "handlers": ["file_server", "file_server_debug"],
        },
        "beaker": {
            "level": "DEBUG",
            "handlers": ["file_debug"],
        },
        "cork": {
            "level": "DEBUG",
            "handlers": ["file_debug"],
        },
        "prov": {
            "level": "DEBUG",
            "handlers": ["file_debug"],
        },
    },
}


# Add the username to the logs
class CustomAdapter(logging.LoggerAdapter):
    """
    This adapter expects the passed in dict-like object to have a
    'username' key, whose value in brackets is appended to the log message.
    """

    def process(self, msg, kwargs):
        return "{} [{}]".format(msg, self.extra["username"]), kwargs


# Create dirs if they do not exist yet
for p in [
    settings.VAR_PATH,
    settings.VAR_PATH + "/db",
    settings.VAR_PATH + "/config",
    settings.LOG_PATH,
    settings.JOBDATA_PATH,
    settings.LOCAL_WORKDIR_PATH,
    settings.RESULTS_PATH,
    settings.UPLOADS_PATH,
    settings.TEMP_PATH,
    settings.JDL_PATH,
    settings.JDL_PATH + "/votable",
    settings.JDL_PATH + "/votable/tmp",
    settings.JDL_PATH + "/votable/saved",
    settings.JDL_PATH + "/scripts",
    settings.JDL_PATH + "/scripts/tmp",
    settings.JDL_PATH + "/scripts/saved",
]:
    if not os.path.isdir(p):
        os.makedirs(p)

# Set logger (need existing /logs in VAR_PATH)
logging.config.dictConfig(LOGGING)
logger_init = logging.getLogger("uws_server")
logger = logger_init
