#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Settings for the UWS server (see base.py for how values are read)
"""

from collections.abc import Callable

from pydantic import ImportString, SecretStr, computed_field, model_validator

from . import generators
from .base import CommonSettings


class ServerSettings(CommonSettings):
    """Settings of the UWS server"""

    ### General settings

    # Set debug mode, HTTP 500 Errors include traceback
    DEBUG: bool = False

    # IP of the web server
    BASE_IP: str = "127.0.0.1"
    LOCAL_USER: str = "www"  # Apache user (may be www, _www, apache...)

    ### Security settings

    # IMPORTANT: use random strings for the following tokens and keep them secret
    JOB_EVENT_TOKEN: SecretStr = SecretStr("TBD")  # TOKEN for special user job_event, used internally
    MAINTENANCE_TOKEN: SecretStr = SecretStr("TBD")  # TOKEN for special user maintenance, used internally

    # Access rules (secure by default, see the Admin guide)
    ALLOW_ANONYMOUS: bool = False  # allow requests without authentication (user anonymous)
    CHECK_PERMISSIONS: bool = True  # check rights to create/edit a job (roles of the user)
    CHECK_OWNER: bool = True  # only owner can access their jobs and files
    # If a user has an APP_TOKEN, access to jobs will be added automatically
    # {"<token>": {"name": "<name>", "active": true, "jobs": ["<jobname1>", "<jobname2>"]}}
    APP_TOKENS: dict[str, dict] = {}

    # Those servers can have access to /job_event/<jobid_manager> to change the phase or report an error
    # The IP can be truncated to allow to refer to a set of IPs
    # Default: localhost and BASE_IP
    JOB_SERVERS: dict[str, str] | None = None
    # The server will allow db and jdl access only from trusted clients (while waiting for an auth system)
    # e.g. /db/init, /jdl/validate... Default: localhost and BASE_IP
    TRUSTED_CLIENTS: dict[str, str] | None = None

    ### Internal settings

    # max active jobs per user
    NJOBS_MAX: int = 0  # 0 for no restriction
    # Default destruction interval
    DESTRUCTION_INTERVAL: int = 30  # in days
    # Maximum and default execution duration, 0 implies unlimited execution duration
    EXECUTION_DURATION_DEF: int = 120  # in seconds
    EXECUTION_DURATION_MAX: int = 3600  # in seconds
    # Maximum wait time (UWS1.1)
    WAIT_TIME_MAX: int = 600  # in seconds
    # Maximum size of a urlencoded request body, or of the non-file fields of a multipart
    # request (bottle.BaseRequest.MEMFILE_MAX, bottle default is 100kB). Uploaded files are
    # not limited by this value (stored on disk). Aligned on nginx client_max_body_size (1m).
    MEMFILE_MAX: int = 1024 * 1024  # in bytes
    # ARCHIVED phase (UWS1.1)
    USE_ARCHIVED_PHASE: bool = True
    # Add the provenance files to the results of the jobs
    GENERATE_PROV: bool = True
    # Copy back results from Manager to UWS server Archive (may be irrelevant if Manager = Local)
    COPY_RESULTS: bool = True
    # Algo for entity hash
    SHA_ALGO: str = "1"  # 1 (default), 224, 256, 384, 512
    # Length of uuid identifiers from the right, max=36
    JOB_ID_LENGTH: int = 6

    # Generators of identifiers, as import strings "module:function" (see
    # opus_config/generators.py for the defaults and signatures, and TOKEN_GEN in base.py)
    JOB_ID_GEN: ImportString[Callable[..., str]] = generators.job_id
    ENTITY_ID_GEN: ImportString[Callable[..., str]] = generators.entity_id

    ### Archive settings

    # Local: store results in the local directory RESULTS_PATH
    # SLURM: specific path accessible from the SLURM work cluster / nodes (given in ARCHIVE_PATH, need also the base access URL)
    # FTP: not implemented
    # VOSpace: not implemented
    ARCHIVE: str = "Local"
    ARCHIVE_PATH: str = ""
    ARCHIVE_URL: str = "/store?ID={ID}"  # use {ID} for the identifier of the result, relative or full URL

    ### Job Description Language (JDL) settings

    # VOTFile: VOTable following the Provenance DM ActivityDescription class
    # WADLFile: WADL file describing the web service
    # WSDLFile: WSDL file describing the web service -- not implemented
    JDL: str = "VOTFile"

    ### Storage settings

    # SQLAlchemy: SQLAlchemy interface to the relational DB, e.g. SQLite, PostgreSQL...)
    STORAGE: str = "SQLAlchemy"
    # SQLite or PostgreSQL
    STORAGE_TYPE: str = "SQLite"
    # SQLite storage type info
    SQLITE_FILE_NAME: str = "job_database.db"
    # PostgreSQL storage type info
    PGSQL_HOST: str = "localhost"
    PGSQL_PORT: int = 5432
    PGSQL_DATABASE: str = "opus"
    PGSQL_USER: str = "opus"
    PGSQL_PASSWORD: SecretStr = SecretStr("opus")

    ### Manager settings

    # Local: execution on the UWS server directly using Bash commands
    # SLURM: execution through a SLURM control manager (additional config required below)
    MANAGER: str = "Local"
    LOCAL_WORKDIR_PATH: str = "/tmp"

    ### SLURM Manager settings

    SLURM_URL: str = "tycho.obspm.fr"
    SLURM_USER: str = "vouws"  # need to add the web server ssh key (e.g. user www) in .ssh/authorized_hosts
    SLURM_MAIL_USER: str | None = None  # Default: ADMIN_EMAIL
    SLURM_SCRIPTS_PATH: str = "/obs/vouws/scripts"
    SLURM_JOBDATA_PATH: str = "/poubelle/vouws/jobdata"
    SLURM_UPLOADS_PATH: str = "/poubelle/vouws/uploads"
    SLURM_WORKDIR_PATH: str = "/scratch/vouws/workdir"
    SLURM_RESULTS_PATH: str = "/poubelle/vouws/results"
    SLURM_SBATCH_DEFAULT: dict[str, int | str] = {
        "nodes": 1,
        "ntasks-per-node": 16,
        "partition": "short",  # for tycho...
        "mem": "1gb",
    }

    @model_validator(mode="after")
    def set_defaults_from_other_settings(self):
        local_ips = {"::1": "localhost", "127.0.0.1": "localhost", self.BASE_IP: "base_ip"}
        if self.JOB_SERVERS is None:
            self.JOB_SERVERS = dict(local_ips)
        if self.TRUSTED_CLIENTS is None:
            self.TRUSTED_CLIENTS = dict(local_ips)
        if self.SLURM_MAIL_USER is None:
            self.SLURM_MAIL_USER = self.ADMIN_EMAIL
        return self

    ### Generate identifiers

    def new_job_id(self):
        return self.JOB_ID_GEN(self.JOB_ID_LENGTH)

    def new_entity_id(self, **kwargs):
        # kwargs contains all the known attributes of an entity
        return self.ENTITY_ID_GEN(self.JOB_ID_LENGTH, **kwargs)

    ### Paths derived from VAR_PATH

    @computed_field
    @property
    def LOG_PATH(self) -> str:
        return self.VAR_PATH + "/logs"

    @computed_field
    @property
    def JDL_PATH(self) -> str:
        # Path for JDL files, should probably be accessed through a URL as static files
        return self.VAR_PATH + "/jdl"

    @computed_field
    @property
    def SCRIPTS_PATH(self) -> str:
        # Path for script files, should probably be accessed through a URL as static files
        return self.VAR_PATH + "/jdl/scripts"

    @computed_field
    @property
    def JOBDATA_PATH(self) -> str:
        # Default path for job results and logs
        return self.VAR_PATH + "/jobdata"

    @computed_field
    @property
    def RESULTS_PATH(self) -> str:
        return self.VAR_PATH + "/results"

    @computed_field
    @property
    def UPLOADS_PATH(self) -> str:
        # If POST contains files they are uploaded on the UWS server
        return self.VAR_PATH + "/uploads"

    @computed_field
    @property
    def TEMP_PATH(self) -> str:
        # Path for e.g. SLURM sbatch files created by SLURMManager
        return self.VAR_PATH + "/temp"

    @computed_field
    @property
    def SQLITE_FILE(self) -> str:
        # Path to sqlite db file
        return self.VAR_PATH + "/db/" + self.SQLITE_FILE_NAME

    @property
    def SQLALCHEMY_DB(self) -> str:
        """Database URL, contains the PostgreSQL password (not a computed field, so not dumped)"""
        if self.STORAGE_TYPE == "PostgreSQL":
            return (
                f"postgresql://{self.PGSQL_USER}:{self.PGSQL_PASSWORD.get_secret_value()}"
                f"@{self.PGSQL_HOST}:{self.PGSQL_PORT}/{self.PGSQL_DATABASE}"
            )
        return "sqlite:///" + self.SQLITE_FILE

    def export(self):
        values = super().export()
        values["SQLALCHEMY_DB"] = self.SQLALCHEMY_DB
        return values
