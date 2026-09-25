#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
""" """

import copy
import datetime as dt
import io
import os
import re
import shutil
import smtplib
import sys
import threading
import traceback
from email.mime.text import MIMEText
from subprocess import CalledProcessError

import requests
from blinker import signal
from bottle import (
    BaseRequest,
    Bottle,
    HTTPError,
    abort,
    redirect,
    request,
    response,
    run,
    static_file,
)

from . import managers, migrate_users, storage, uws_jdl
from .settings import (
    settings,
    ACTIVE_PHASES,
    APP_PATH,
    CustomAdapter,
    DT_FMT,
    PHASES,
    PHASE_CONVERT,
    TERMINAL_PHASES,
    logger,
    logger_init,
)
from .uws_classes import (
    EntityAccessDenied,
    Job,
    JobAccessDenied,
    JobList,
    ParameterTooLong,
    TooManyJobs,
    User,
    special_users,
)

# Note: this import will also import .settings

# Create a new application
app = Bottle()
BaseRequest.MEMFILE_MAX = settings.MEMFILE_MAX

# Warn if the users table was created by a previous version (see migrate_users.py)
migrate_users.check_users_schema()


# ----------
# Set user
# ----------


# Handling the OPTIONS method
# https://github.com/bottlepy/bottle/issues/402
@app.route("/<:re:.*>", method="OPTIONS")
def options_request():
    # response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header(
        "Access-Control-Allow-Headers", "Authorization, X-Requested-With"
    )
    # pass


# @app.hook('after_request')
# def enableCORSAfterRequestHook():
#    response.set_header('Access-Control-Allow-Origin', '*')


# @hook('after_request')
# def enable_cors():
#    response.headers['Access-Control-Allow-Origin'] = '*'


@app.hook("before_request")
def strip_path():
    request.environ["PATH_INFO"] = request.environ["PATH_INFO"].rstrip("/")


# @app.hook('before_request')
def set_user(jobname=None):
    global logger
    """Set user from request header"""
    # Use anonymous as default
    user_name = "anonymous"
    user_token = "anonymous"
    user = User(user_name, user_token)
    # Check if REMOTE_USER is set by web server or use Basic Auth from header
    if request.auth:
        user_name, user_token = request.auth
        if not user_token:
            user_token = "remote_user"
        # logger.debug('{}:{}'.format(user_name, user_token))
    # # Set user from GET
    # if 'user' in request.GET:
    #     user_name = request.GET['user']
    #     if 'user_token' in request.GET:
    #         user_token = request.GET['user_token']
    #     else:
    #         user_token = request.GET['user']
    #     logger.debug('user information from GET ({}:{})'.format(user_name, user_token))
    # # Set user from REMOTE_USER if not empty
    # remote_user = request.environ.get('REMOTE_USER', '')
    # if remote_user:
    #     user_name = remote_user
    #     user_token = remote_user
    #     logger.debug('REMOTE_USER is set: {}'.format(user_name))
    # # Use Basic access authentication
    # auth = request.headers.get('Authorization')
    # Using WSGI, the header is changed to HTTP_AUTHORIZATION
    # if not auth:
    #     auth = request.headers.get('HTTP_AUTHORIZATION')
    # if auth:
    #     logger.debug('Authorization: {}'.format(auth))
    #     user_name, user_token = parse_auth(auth)
    #     logger.debug('Authorization: {}:{}'.format(user_name, user_token))
    # Create user object
    if user_name:
        user = User(user_name, user_token)
    # Add user name at the end of each log entry
    logger = CustomAdapter(logger_init, {"username": user.name})
    if user == User("anonymous", "anonymous") and not settings.ALLOW_ANONYMOUS:
        abort_403("User anomymous not allowed on this server")
    # Add user if not in db
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    job_storage.add_user(user.name, token=user.token)
    # Check and add roles from APP_TOKEN
    if settings.APP_TOKENS and user_token in settings.APP_TOKENS:
        # An application token was found and roles will be added
        active = settings.APP_TOKENS[user_token]["active"]
        app_name = settings.APP_TOKENS[user_token]["name"]
        app_jobs = settings.APP_TOKENS[user_token]["jobs"]
        logger.debug(
            f"APP_TOKEN {app_name} found for user {user_name}, roles associated: {app_jobs}"
        )
        for jobname in app_jobs:
            if job_storage.has_role(user_name, user_token, jobname):
                if not active:
                    job_storage.remove_role(user_name, user_token, role=jobname)
            else:
                if active:
                    job_storage.add_role(user_name, user_token, role=jobname)
    return user


def get_real_ip():
    # logger.debug(request.remote_addr)
    # logger.debug(request.environ.get('HTTP_X_REAL_IP'))
    # logger.debug(request.environ.get('HTTP_X_FORWARDED_FOR'))
    ip = request.environ.get(
        "HTTP_X_REAL_IP",
        request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr),
    )
    return ip


def is_job_server(func):
    """Test if request comes from a job server"""

    def is_job_server_wrapper(*args, **kwargs):
        # IP or part of an IP has to be in the JOB_SERVERS list
        ip = get_real_ip()
        matching = [x for x in settings.JOB_SERVERS if x in ip]
        if matching:
            logger.info(
                f"Access authorized to {request.urlparts.path} for {ip} ({settings.JOB_SERVERS[matching[0]]})"
            )
            pass
        else:
            abort_403(f"{ip} is not a job server")
        return func(*args, **kwargs)

    return is_job_server_wrapper


def is_client_trusted(func):
    """Test if request comes from a trusted client"""

    def is_client_trusted_wrapper(*args, **kwargs):
        # IP or part of an IP has to be in the TRUSTED_CLIENTS list
        ip = get_real_ip()
        matching = [x for x in settings.TRUSTED_CLIENTS if x in ip]
        if matching:
            logger.info(
                f"Access authorized to {request.urlparts.path} for {ip} ({settings.TRUSTED_CLIENTS[matching[0]]})"
            )
            pass
        else:
            abort_403(f"{ip} is not a trusted client")
        return func(*args, **kwargs)

    return is_client_trusted_wrapper


def is_localhost(func):
    """Test if localhost"""

    def is_localhost_wrapper(*args, **kwargs):
        ip = get_real_ip()
        if ip != settings.BASE_IP and ip != "::1" and ip != "127.0.0.1":
            abort_403(f"{ip} is not localhost")
        return func(*args, **kwargs)

    return is_localhost_wrapper


def is_admin(func):
    """Decorator to test if user is the admin
    :param func:
    :return:
    """

    def is_admin_wrapper(*args, **kwargs):
        user = set_user()
        if not user.check_admin():
            abort_403(f"{user.name} is not an admin")
        return func(*args, **kwargs)

    return is_admin_wrapper


# ----------
# Abort functions
# ----------


class BadRequestError(Exception):
    pass


def abort_400(msg=""):
    """HTTP Error 400

    Returns:
        400 Bad Request
    """
    logger.warning(f"Bad Request: {msg} ({request.urlparts.path})")
    abort(400, f"{msg}")


def abort_403(msg=""):
    """HTTP Error 403

    Returns:
        403 Forbidden
    """
    logger.warning(f"Forbidden: {msg} ({request.urlparts.path})")
    abort(403, f"{msg}")
    # abort(403, 'You don\'t have permission to access {} on this server. \n{}'
    #            ''.format(request.urlparts.path, msg))


def abort_404(msg=None):
    """HTTP Error 404

    Returns:
        404 Not Found
        404 Not Found + message
    """
    if msg:
        logger.warning(f"Not Found: {msg} ({request.urlparts.path})")
        abort(404, msg)
    else:
        logger.warning("Not Found")
        abort(404)


def abort_500(msg=None):
    """HTTP Error 500

    Returns:
        500 Internal Server Error
        500 Internal Server Error + message
    """
    if msg:
        logger.warning(msg)
        abort(500, msg)
    else:
        logger.warning("Internal Server Error")
        abort(500)


def abort_500_except(msg=None, msg_public=None):
    """Show exception and traceback on web page if DEBUG=true

    Returns:
        HTTPError status if the exception is an HTTPError
        500 Internal Server Error
        500 Internal Server Error + traceback (on DEBUG=true)
    """
    # message = "{0}: {1!r}".format(type().__name__, ex.args)
    exc_info = sys.exc_info()
    # Keep status of HTTPError raised in the try block (e.g. 413 from bottle, 403, 404)
    if isinstance(exc_info[1], HTTPError):
        logger.warning(f"{exc_info[1].status}: {exc_info[1].body}")
        raise exc_info[1]
    tb = traceback.format_exception(*exc_info)
    message = "".join(tb)
    if msg:
        message += msg
    logger.error("\n" + message)
    if settings.DEBUG:
        abort(500, message)
    else:
        if not msg_public:
            msg_public = "Internal Server Error"
        abort(500, msg_public)


# ----------
# Helper functions
# ----------


@app.route("/")
def home():
    # TODO: server and client may have different URLS...
    logger.info("Access to home page")
    logger.info("  Python sys.version: " + sys.version.replace("\n", " "))
    logger.info("  Python sys.exec_prefix: " + sys.exec_prefix)
    resp_status_code = 0
    try:
        client_url = settings.UWS_CLIENT_ENDPOINT
        if "http" not in client_url:
            client_url = settings.BASE_URL + settings.UWS_CLIENT_ENDPOINT
        resp = requests.get(client_url)
        resp_status_code = resp.status_code
    except Exception as e:
        msg_txt = "Client is not responding"
        logger.warning(msg_txt)
        logger.warning(repr(e))
    if resp_status_code == 200:
        logger.info("Redirect to client: " + client_url)
        redirect(client_url)
    return "OPUS - https://opus-job-manager.readthedocs.io"


@app.route("/favicon.ico")
def favicon():
    return static_file("favicon.ico", root=APP_PATH)


def send_mail(send_to, subject, msg):
    try:
        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        # server.starttls()
        # server.login("YOUR EMAIL ADDRESS", "YOUR PASSWORD")
        mail_text = MIMEText(msg, "plain")
        mail_text["Subject"] = subject
        mail_text["From"] = settings.SENDER_EMAIL
        mail_text["To"] = send_to
        server.sendmail(settings.SENDER_EMAIL, send_to, mail_text.as_string())
        server.quit()
    except Exception:
        logger.error("Unable to send email")
        raise HTTPError(424, "Unable to send email") from None


# ----------
# SCIM v2 API for user management
# ----------


@app.get(settings.SCIM_ENDPOINT + "/ServiceProviderConfig")
def scim_ServiceProviderConfig():
    scim_config = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": False},
        "bulk": {"supported": False, "maxOperations": 1000, "maxPayloadSize": 1048576},
        "filter": {"supported": False, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [{"type": "httpbasic", "name": "HTTP Basic"}],
    }
    # response.content_type = 'application/json; charset=UTF-8'
    return scim_config


@app.get(settings.SCIM_ENDPOINT + "/Schemas")
def scim_Schemas():
    scim_schemas = {
        "id": "urn:ietf:params:scim:schemas:core:2.0:User",
        "name": "User",
        "description": "User Account",
        "attributes": [
            {
                "name": "userName",
                "type": "string",
                "multiValued": False,
                "description": "Unique identifier for the User, typically used by the user to directly authenticate to the service provider. Each User MUST include a non-empty userName value.  This identifier MUST be unique across the service provider's entire set of Users. REQUIRED.",
                "required": True,
                "caseExact": False,
                "mutability": "readWrite",
                "returned": "default",
                "uniqueness": "server",
            },
            {
                "name": "token",
                "type": "string",
                "multiValued": False,
                "description": "The User's token.",
                "required": True,
                "caseExact": True,
                "mutability": "writeOnly",
                "returned": "never",
                "uniqueness": "none",
            },
            {
                "name": "roles",
                "type": "string",
                "multiValued": True,
                "description": "A coma-separated list of roles for the User",
                "required": False,
                "mutability": "readWrite",
                "returned": "default",
            },
            {
                "name": "active",
                "type": "boolean",
                "multiValued": False,
                "description": "A Boolean value indicating the User's administrative status.",
                "required": False,
                "mutability": "readWrite",
                "returned": "default",
            },
        ],
    }
    return scim_schemas


@app.get(settings.SCIM_ENDPOINT + "/ResourceTypes")
def scim_ResourceTypes():
    scim_resourcetypes = {
        "itemsPerPage": 1,
        "startIndex": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "Users",
                "name": "User",
                "endpoint": "/Users",
                "description": "User Account",
                "schema": "urn:scim:schemas:core:2.0:User",
            }
        ],
    }
    return scim_resourcetypes


@app.get(settings.SCIM_ENDPOINT + "/ResourceTypes/User")
def scim_ResourceTypes_User():
    scim_resourcetypes = {
        "id": "Users",
        "schemas": ["urn:scim:schemas:core:2.0:ResourceType"],
        "name": "User",
        "description": "Core User",
        "endpoint": "/Users",
        "schema": "urn:scim:schemas:core:2.0:User",
    }
    return scim_resourcetypes


def user2scim(u):
    user_dict = {
        "schemas": ["urn:scim:schemas:core:2.0:User"],
        "id": u["name"],
        "userName": u["name"],
        "meta": {
            "resourceType": "User",
            "created": str(u["first_connection"]),
            "lastModified": str(u["first_connection"]),
            "location": "scim/v2/Users/" + u["name"],
        },
    }
    for attr in ["token", "roles", "active"]:
        user_dict[attr] = u[attr]
    return user_dict


@app.get(settings.SCIM_ENDPOINT + "/Users")
@is_client_trusted
@is_admin
def get_users():
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    users = job_storage.get_users()
    scim_user_resources = []
    for u in users:
        # do not expose opus-admin
        if u["name"] != settings.ADMIN_NAME:
            scim_user_resources.append(user2scim(u))
    scim_users = {
        "itemsPerPage": 10000,
        "startIndex": 1,
        "Resources": scim_user_resources,
    }
    return scim_users


@app.post(settings.SCIM_ENDPOINT + "/Users")
@is_client_trusted
@is_admin
def create_user():
    name = request.POST.get("name", "")
    if name:
        token = request.POST.get("token", "")
        roles = request.POST.get("roles", None)
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        job_storage.add_user(name, token=token, roles=roles)
        # the same name may have several accounts (one per token)
        users = job_storage.get_users(name=name, token=token or None)
        if users:
            u = users[0]
            logger.info("User created: " + name)
            return user2scim(u)
        else:
            abort_404(f"No user found with name {name}")
    else:
        abort_500("No user name provided")


@app.get(settings.SCIM_ENDPOINT + "/Users/<name>")
@is_client_trusted
@is_admin
def get_user(name):
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    # the same name may have several accounts (one per token)
    token = request.query.get("token", None)
    users = job_storage.get_users(name=name, token=token)
    if len(users) > 1:
        abort(409, f"{len(users)} accounts found with name {name}, give the token")
    if users:
        u = users[0]
        return user2scim(u)
    else:
        abort_404(f"No user found with name {name}")


@app.post(settings.SCIM_ENDPOINT + "/Users/<name>")
@is_client_trusted
@is_admin
def patch_user(name):
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    token = request.POST.get("user_token", None)
    if token:
        users = job_storage.get_users(name=name, token=token)
        u = users[0]
        if u:
            for k in request.POST:
                if k in ["token", "roles", "active"]:
                    u[k] = request.POST[k]
                    # save modified user
                    job_storage.update_user(name, k, request.POST[k], token=token)
                    logger.info("User patched: " + name)
            return user2scim(u)
        else:
            abort_404(f"No user found with name {name}")
    else:
        abort_404(f"No token found for user name {name}")


@app.route(settings.SCIM_ENDPOINT + "/Users/<name>", method="DELETE")
@is_client_trusted
@is_admin
def delete_user(name):
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    token = request.POST.get("user_token", None)
    username = job_storage.remove_user(name, token=token)
    if username:
        logger.info("User deleted: " + username)
        response.content_type = "text/plain; charset=UTF-8"
        response.status = 200
        return "Success"
    else:
        abort_500(f"No user deleted (name: {name})")


# ----------
# JDL functions
# ----------

# /jdl = list of job descriptions
# /jdl/<jobname> = description for this job (json ? votable ?)
# /jdl/<jobname>/votable
# /jdl/<jobname>/json
# /jdl/<jobname>/script
# /jdl/<jobname> POST = create or modify
# /jdl/<jobname> DELETE = delete
# /jdl/<jobname>/activate
# /jdl/<jobname>/deactivate
# /jdl/<jobname>/copy_script (to job cluster)


@app.get("/jdl")
def get_jobnames():
    """
    Get list of available jobs on server
    :return: list of job names in json
    """
    user = set_user()
    try:
        # jobnames = ['copy', 'ctbin']
        # List jdl files (=available jobs)
        jdl = getattr(uws_jdl, settings.JDL)()
        jobnames_all = jdl.get_jobnames()
        jobnames = []
        if not settings.CHECK_PERMISSIONS or user.check_admin():
            jobnames = jobnames_all
        else:
            # keep jobnames accessible to user
            # db = storage.__dict__[STORAGE + 'JobStorage']()
            db = getattr(storage, settings.STORAGE + "JobStorage")()
            roles = db.get_roles(user)
            if "all" in roles:
                jobnames = jobnames_all
            else:
                jobnames = [j for j in jobnames_all if j in roles]
        jobnames.sort()
        details = {}
        for j in jobnames:
            # Get JDL
            jdl.read(j)
            # map some information
            details[j] = copy.copy(jdl.content)
        jobnames_json = {"jobnames": jobnames, "details": details}
        return jobnames_json
    except UserWarning as e:
        abort_404(e.args[0])


# @app.post('/config/job_definition')
@app.post("/jdl")
@is_client_trusted
def create_new_job_definition():
    """Use posted parameters to create a new JDL file for the given job"""
    # No need to authenticate, users can propose new jobs that will have to be validated
    # Check if client is trusted? not really needed
    jobname = ""
    user = set_user()
    try:
        jobname = request.forms.get("name").split("/")[-1]
        if jobname:
            # Create JDL file from job_jdl
            # jdl = uws_jdl.__dict__[JDL]()
            jdl = getattr(uws_jdl, settings.JDL)()
            jdl.set_from_post(request.forms, user)
            # Save as a new job description
            jdl.save("tmp/" + jobname)
        else:
            abort_500("No jobname given")
    except Exception:
        abort_500_except()
    # Response
    return {"jobname": jobname}


@app.post("/jdl/import_jdl")
@is_client_trusted
def import_job_definition():
    """Use posted parameters to create a new JDL file for the given job"""
    # No need to authenticate, users can propose new jobs that will have to be validated
    # Check if client is trusted? not really needed
    jobname = ""
    user = set_user()
    try:
        # Save JDL file as new for this jobname
        f = request.files.get("jdl_file", None)
        if f:
            # now = dt.datetime.now().isoformat().split('.')[0]
            # Get jobname from file name (?)
            jdl = getattr(uws_jdl, settings.JDL)()
            jobname = f.filename.split(jdl.extension)[
                0
            ]  # e.g. remove _vot.xml at the end of filename
            if jobname == f.filename:  # else remove extension
                jobname = os.path.splitext(os.path.basename(f.filename))[0]
            if jobname:
                logger.debug(jobname)
                fname_temp = jdl._get_filename("tmp/" + jobname)
                logger.debug(fname_temp)
                if os.path.isfile(fname_temp):
                    os.remove(fname_temp)
                f.save(fname_temp)
                # Read JDL
                logger.debug("tmp/" + jobname)
                jdl.read("tmp/" + jobname)
                if jdl.content["name"]:
                    if jdl.content["name"] != jobname:
                        logger.warning(
                            "Jobname and filename not matching, JDL renamed: {} ({})".format(
                                jdl.content["name"], f.filename
                            )
                        )
                        jobname = jdl.content["name"]
                        fname_mv = jdl._get_filename("tmp/" + jobname)
                        shutil.move(fname_temp, fname_mv)
                else:
                    logger.warning(
                        f"No jobname found, using filename to define jobname: {jobname} ({f.filename})"
                    )
                    jdl.content["name"] = jobname
                # Save JDL
                jdl.save("tmp/" + jobname)
            else:
                abort_500("No jobname found for file " + f.filename)
    except Exception:
        abort_500_except()
    # Return code 200 and jobname
    return {"jobname": jobname}
    # redirect('/client/job_definition?jobname={}&msg=validated'.format(jobname), 303)


@app.post("/jdl/tmp/<jobname>/validation_request")
@is_client_trusted
def validation_request_job_definition(jobname):
    """Use filled form to create a JDL file for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    user = set_user()
    try:
        jdl = getattr(uws_jdl, settings.JDL)()
        jdl_src = f"{jdl.jdl_path}/tmp/{jobname}{jdl.extension}"
        if os.path.isfile(jdl_src):
            # send email to admin
            # mail.
            mail_subject = f"OPUS job validation request: {jobname}"
            mail_text = f"{mail_subject}\n{settings.BASE_URL}/jdl/tmp/{jobname}/json\n(from: {user.name})"
            send_mail(settings.ADMIN_EMAIL, mail_subject, mail_text)
            logger.info("Validation request sent to admin: " + jobname)
        else:
            logger.info("No JDL  found for validation: " + jdl_src)
            abort_500("No JDL file found for " + jobname)
    except HTTPError as e:
        raise e
    except Exception:
        abort_500_except()
    # Return code 200
    return {"jobname": jobname}


# @app.get('/config/validate_job/<jobname>')
@app.post("/jdl/tmp/<jobname>/validate")
@is_client_trusted
@is_admin
def validate_job_definition(jobname):
    """Use filled form to create a JDL file for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    try:
        # Copy script and jdl from new
        # jdl = uws_jdl.__dict__[JDL]()
        jdl = getattr(uws_jdl, settings.JDL)()
        jdl_src = f"{jdl.jdl_path}/tmp/{jobname}{jdl.extension}"
        jdl_dst = f"{jdl.jdl_path}/{jobname}{jdl.extension}"
        script_src = f"{jdl.scripts_path}/tmp/{jobname}.sh"
        script_dst = f"{jdl.scripts_path}/{jobname}.sh"
        # Save, then copy from tmp/
        if os.path.isfile(jdl_src):
            if os.path.isfile(jdl_dst):
                # Save file with version and time stamp
                mt = (
                    dt.datetime.fromtimestamp(os.path.getmtime(jdl_dst))
                    .isoformat()
                    .split(".")[0]
                )
                jdl.read(jobname)  # need version for saved files
                jdl_dst_save = "{}/saved/{}_v{}_{}{}".format(
                    jdl.jdl_path, jobname, jdl.content["version"], mt, jdl.extension
                )
                os.rename(jdl_dst, jdl_dst_save)
                logger.info("Previous job JDL saved: " + jdl_dst_save)
            shutil.copy(jdl_src, jdl_dst)
            logger.info("Job JDL file copied: " + jdl_dst)
        else:
            logger.info("No JDL  found for validation: " + jdl_src)
            abort_500("No JDL file found for " + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
        if os.path.isfile(script_src):
            if os.path.isfile(script_dst):
                # Save file with time stamp
                mt = (
                    dt.datetime.fromtimestamp(os.path.getmtime(script_dst))
                    .isoformat()
                    .split(".")[0]
                )
                jdl.read(jobname)  # need version for saved files
                script_dst_save = "{}/saved/{}_v{}_{}.sh".format(
                    settings.SCRIPTS_PATH, jobname, jdl.content["version"], mt
                )
                os.rename(script_dst, script_dst_save)
                logger.info("Previous job script saved: " + script_dst_save)
            shutil.copy(script_src, script_dst)
            logger.info("Job script copied: " + script_dst)
            # Copy script to job manager
            # manager = managers.__dict__[MANAGER + 'Manager']()
            manager = getattr(managers, settings.MANAGER + "Manager")()
            manager.cp_script(jobname)
            logger.info("Job script copied to work cluster: " + jobname)
        else:
            logger.info("No job script found for validation: " + script_src)
            abort_500("No job script found for " + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except Exception:
        abort_500_except()
    # Return code 200
    return {"jobname": jobname}
    # redirect('/client/job_definition?jobname={}&msg=validated'.format(jobname), 303)


@app.get("/jdl/<jobname:path>/convert")
@is_client_trusted
@is_admin
def convert_jdl(jobname):
    """
    Get json description file for jobname
    :param jobname:
    :return: json description
    """
    try:
        # logger.info(jobname)
        uws_jdl.update_vot(jobname)
    except UserWarning as e:
        abort_404(e.args[0])
    except Exception:
        abort_500_except()
    return f"JDL converted for {jobname}"


# @app.get('/config/cp_script/<jobname>')
@app.post("/jdl/<jobname:path>/copy_script")
@is_client_trusted
@is_admin
def cp_script(jobname):
    """copy script to job manager for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    try:
        # Copy script to job manager
        script_dst = f"{settings.SCRIPTS_PATH}/{jobname}.sh"
        if os.path.isfile(script_dst):
            # manager = managers.__dict__[MANAGER + 'Manager']()
            manager = getattr(managers, settings.MANAGER + "Manager")()
            manager.cp_script(jobname)
            logger.info("Job script copied to work cluster: " + jobname)
        else:
            logger.info("No job script found for job: " + jobname)
            abort_500("No job script found for " + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except Exception:
        abort_500_except()
    # Return code 200
    response.content_type = "text/plain; charset=UTF-8"
    return f"Script copied for job {jobname}"
    # redirect('/client/job_definition?jobname={}&msg=script_copied'.format(jobname), 303)


@app.get("/jdl/<jobname:path>/script")
def get_script(jobname):
    """
    Get script file as text
    :param jobname:
    :return:
    """
    # user = set_user()
    # db = getattr(storage, STORAGE + 'JobStorage')()
    # if db.has_access(user, jobname):
    #     fname = '{}/{}.sh'.format(SCRIPTS_PATH, jobname)
    #     if os.path.isfile(fname):
    #         response.content_type = 'text/plain; charset=UTF-8'
    #         logger.info('Job script downloaded: {}'.format(fname))
    #         return static_file(fname, root='/', mimetype='text')
    #     abort_404('No script file found for ' + jobname)
    # else:
    #     abort_403()
    user = set_user()
    try:
        db = getattr(storage, settings.STORAGE + "JobStorage")()
        if not settings.CHECK_PERMISSIONS or db.has_access(user, jobname):
            # Get JDL content
            jdl = getattr(uws_jdl, settings.JDL)()
            jdl.read_script(jobname)
            logger.info(f"Job script downloaded: {jobname}")
            response.content_type = "text/plain; charset=UTF-8"
            return jdl.content["script"]
        else:
            abort_403()
    except UserWarning as e:
        abort_404(e.args[0])
    except Exception:
        abort_500_except()


@app.get("/jdl/<jobname:path>/json")
def get_jdl_json(jobname):
    """
    Get json description file for jobname
    :param jobname:
    :return: json description
    """
    user = set_user()
    try:
        getattr(storage, settings.STORAGE + "JobStorage")()
        # if not CHECK_PERMISSIONS or db.has_access(user, jobname) or 'tmp/' in jobname:
        # Get JDL content
        jdl = getattr(uws_jdl, settings.JDL)()
        jdl.read(jobname)
        logger.debug(f"JDL downloaded ad JSON: {jobname}")
        return jdl.content
        # else:
        #     abort_403()
    except UserWarning as e:
        abort_404(e.args[0])
    except Exception:
        abort_500_except()


@app.get("/jdl/<jobname>")
def get_jdl(jobname):
    """
    Get JDL file for jobname
    :param jobname:
    :return: VOTable file
    """
    # logger.info(jobname)
    # user = set_user()
    try:
        # db = getattr(storage, STORAGE + "JobStorage")()
        # if not CHECK_PERMISSIONS or db.has_access(user, jobname):
        # Get JDL content
        jdl = getattr(uws_jdl, settings.JDL)()
        fname = jdl._get_filename(jobname)
        download_dir, download_fname = os.path.split(fname)
        logger.debug(download_fname)
        if os.path.isfile(fname):
            with open(fname) as f:
                jdl = f.readlines()
            logger.debug(f"JDL file downloaded: {fname}")
            return static_file(
                download_fname, root=download_dir, download=download_fname
            )
            # response.content_type = 'text/xml; charset=UTF-8'
            # return jdl
        else:
            abort_404("No VOTable file found for " + jobname)
        # else:
        #     abort_403()
    except UserWarning as e:
        abort_404(e.args[0])
    except Exception:
        abort_500_except()


@app.delete("/jdl/<jobname>")
@is_client_trusted
@is_admin
def delete_jdl(jobname):
    """
    Delete jdl with
    :param jobname:
    :return:
    """
    try:
        jdl = getattr(uws_jdl, settings.JDL)()
        jdl.read(jobname)  # need version for saved files
        jdl_src = f"{jdl.jdl_path}/{jobname}{jdl.extension}"
        script_src = f"{jdl.scripts_path}/{jobname}.sh"
        if os.path.isfile(jdl_src):
            # Save file with version and time stamp
            mt = (
                dt.datetime.fromtimestamp(os.path.getmtime(jdl_src))
                .isoformat()
                .split(".")[0]
            )
            jdl_dst_save = "{}/saved/{}_v{}_{}_DELETED{}".format(
                jdl.jdl_path, jobname, jdl.content["version"], mt, jdl.extension
            )
            shutil.move(jdl_src, jdl_dst_save)
            logger.info("JDL file archived and deleted: " + jdl_dst_save)
        else:
            logger.warning("No JDL file found: " + jdl_src)
            abort_500("No JDL file found for " + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
        if os.path.isfile(script_src):
            # Save file with time stamp
            mt = (
                dt.datetime.fromtimestamp(os.path.getmtime(script_src))
                .isoformat()
                .split(".")[0]
            )
            script_dst_save = "{}/saved/{}_v{}_{}_DELETED.sh".format(
                settings.SCRIPTS_PATH, jobname, jdl.content["version"], mt
            )
            shutil.move(script_src, script_dst_save)
            logger.info("Job script archived and deleted: " + script_dst_save)
        else:
            logger.warning("No job script found: " + script_src)
            abort_500("No job script found for " + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except Exception:
        abort_500_except()
    # Return code 200
    return {"jobname": jobname}


# ----------
# Results and provenance
# ----------


@app.route("/store/<eid>/<fname>")
def get_result_file(eid, fname):
    redirect(settings.BASE_URL + "/store?ID=" + eid, 303)


@app.route("/store")
def download_entity():
    """Get entity file corresponding to ID=entity_id

    Returns:
        200 OK: file (on success)
        403 Forbidden
        404 Not Found: Entity not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        if "ID" not in request.query:
            raise UserWarning('"ID" is not specified in request') from None
        entity_id = request.query["ID"]
        # logger.debug('Init storage for entity {}'.format(entity_id))
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        entity = job_storage.get_entity(entity_id)

        if settings.CHECK_OWNER:
            if user in special_users:
                pass
            else:
                if entity["owner"] == user.name:
                    pass
                else:
                    raise EntityAccessDenied(
                        f"User {user.name} is not the owner of the entity"
                    )

        download = (
            entity["entity_id"] + "_" + entity["file_name"]
        )  #  + os.path.splitext(entity['file_name'])[1]
        logger.debug(f"{str(entity)}")
        response.set_header("Content-type", entity["content_type"])
        return static_file(
            entity["file_name"],
            root=entity["file_dir"],
            mimetype=entity["content_type"],
            download=download,
        )
        # if any(x in entity['content_type'] for x in ['text', 'xml', 'json', 'image/png', 'image/jpeg']):
        #     return static_file(entity['file_name'], root=entity['file_dir'], mimetype=entity['content_type'],
        #                        download=download)
        # else:
        #     response.set_header('Content-Disposition', 'attachment; filename="{}"'.format(entity['file_name']))
        #     return static_file(entity['file_name'], root=entity['file_dir'], mimetype=entity['content_type'],
        #                        download=download)
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()


# TODO: function will be deprecated (replaced by /store)
@app.route("/store_old/<jobid>/<rname>")  # /<rfname>')
def get_result_file_old(jobid, rname):  # , rfname):
    """Get result file <rname> for job <jobid>

    Returns:
        200 OK: file (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        # Get job properties from DB
        job = Job("", jobid, user, get_attributes=False, get_results=True)
        try:
            # Check if result exists
            if rname not in job.results:
                raise storage.NotFoundWarning(
                    f'Result "{rname}" NOT FOUND for job "{jobid}"'
                )
            # Return result
            result_details = {
                "stdout": "stdout.log",
                "stderr": "stderr.log",
                "provjson": "provenance.json",
                "provxml": "provenance.xml",
                "provsvg": "provenance.svg",
            }
            if rname in result_details:
                rfname = result_details[rname]
            else:
                rfname = job.get_result_filename(rname)
            if rname in ["stdout", "stderr"]:
                return static_file(
                    rfname, root=f"{settings.JOBDATA_PATH}/{job.jobid}", mimetype="text"
                )
            # response.content_type = 'text/plain; charset=UTF-8'
            # return str(job.results[result]['url'])
            content_type = job.results[rname]["content_type"]
            logger.debug(f"{job.jobname} {jobid} {rname} {rfname} {content_type}")
            response.set_header("Content-type", content_type)
            if any(
                x in content_type
                for x in ["text", "xml", "json", "image/png", "image/jpeg"]
            ):
                return static_file(
                    rfname,
                    root=f"{settings.RESULTS_PATH}/{job.jobid}",
                    mimetype=content_type,
                )
            else:
                response.set_header(
                    "Content-Disposition", f'attachment; filename="{rfname}"'
                )
                return static_file(
                    rfname,
                    root=f"{settings.RESULTS_PATH}/{job.jobid}",
                    mimetype=content_type,
                    download=True,
                )
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.get("/provsap")
def provsap():
    """Get provenance for job/entity following IVOA ProvSAP

    Returns:
        200 OK: file (on success)
        403 Forbidden
        404 Not Found: Entity not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """

    from . import provenance

    user = set_user()
    try:
        if "ID" not in request.query:
            raise UserWarning('"ID" is not specified in request') from None
        kwargs = {}
        kwargs["depth"] = request.query.get("DEPTH", 1)
        kwargs["model"] = request.query.get("MODEL", "IVOA")
        kwargs["direction"] = request.query.get("DIRECTION", "BACK")
        kwargs["agents"] = int(request.query.get("AGENTS", 1))
        kwargs["members"] = int(request.query.get("MEMBERS", 0))
        kwargs["descriptions"] = int(request.query.get("DESCRIPTIONS", 0))
        kwargs["configuration"] = int(request.query.get("CONFIGURATION", 1))
        respformat = request.query.get("RESPONSEFORMAT", "PROV-SVG")
        attributes = int(request.query.get("ATTRIBUTES", 1))
        gd = request.query.get("GD", "LR")
        if kwargs["depth"] == "ALL":
            kwargs["depth"] = -1
        else:
            kwargs["depth"] = int(kwargs["depth"])
        ids = request.query.getall("ID")
        pdocs = []
        for id in ids:
            show_generated = True
            # Test if ID is an entity_id, and get the related jobid (that generated the entity)
            job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
            entity = job_storage.get_entity(id, silent=True)
            if entity:
                jobid = entity.get("jobid")
                show_generated = True
                if kwargs["depth"] > 0:
                    kwargs["depth"] -= 1
            else:
                # Then it must be a jobid
                jobid = id
            # Get job properties from DB
            # job = Job('', jobid, user, get_attributes=True, get_parameters=True, get_results=True)
            # logger.info('{} {}'.format(job.jobname, jobid))
            # Return job provenance
            logger.debug(f"{kwargs}")
            pdoc = provenance.job2prov(
                jobid, user, show_generated=show_generated, **kwargs
            )
            pdocs.append(pdoc)
        # Merge all pdocs
        pdoc = pdocs.pop()
        for opdoc in pdocs:
            pdoc.update(opdoc)
        pdoc.unified()

        filename_base = "provsap_" + "_".join(ids)
        if respformat == "PROV-SVG":
            svg_content = provenance.prov2svg_content(
                pdoc, attributes=attributes, direction=gd
            )
            response.content_type = "text/xml"
            response.headers["Content-Disposition"] = (
                'filename="' + filename_base + '.svg"'
            )
            return svg_content
        elif respformat == "PROV-PNG":
            png_content = provenance.prov2png_content(
                pdoc, attributes=attributes, direction=gd
            )
            response.content_type = "image/png"
            response.headers["Content-Disposition"] = (
                'filename="' + filename_base + '.png"'
            )
            return png_content
        elif respformat == "PROV-XML":
            result = io.BytesIO()
            pdoc.serialize(result, format="xml")
            result.seek(0)
            response.content_type = "text/xml; charset=UTF-8"
            response.headers["Content-Disposition"] = (
                'filename="' + filename_base + '.xml"'
            )
            return b"\n".join(result.readlines())
        elif respformat == "PROV-JSON":  # return PROV-JSON as default
            result = io.BytesIO()
            pdoc.serialize(result, format="json")
            result.seek(0)
            response.content_type = "application/json; charset=UTF-8"
            response.headers["Content-Disposition"] = (
                'filename="' + filename_base + '.json"'
            )
            return b"\n".join(result.readlines())
        else:
            raise BadRequestError(
                f"Bad value for RESPONSEFORMAT ({format}).\nAvailable values are ('PROV-JSON', 'PROV-XML', 'PROV-SVG')."
            )
    except BadRequestError as e:
        abort_400(e.args[0])
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


# ----------
# Server maintenance
# ----------


@app.route("/handler/maintenance/<jobname>")
@is_localhost
def maintenance(jobname):
    """Performs server maintenance, e.g. executed regularly by the server itself (localhost)

    Returns:
        200 OK: text/plain (on success)
        403 Forbidden (if not localhost)
        500 Internal Server Error (on error)
    """
    global logger
    report = []
    try:
        user = User("maintenance", settings.MAINTENANCE_TOKEN.get_secret_value())
        logger = logger_init
        if jobname != "__all__":
            jobnames = [jobname]
        else:
            jdl = getattr(uws_jdl, settings.JDL)()
            jobnames = jdl.get_jobnames()
        for jobname in jobnames:
            report.append(f"Maintenance checks for {jobname}...")
            # Get joblist
            joblist = JobList(jobname, user, where_owner=False, include_archived=True)
            try:
                now = dt.datetime.now()
                for j in joblist.jobs:
                    # For each job:
                    job = Job(
                        jobname,
                        j["jobid"],
                        user,
                        get_attributes=True,
                        get_parameters=True,
                        get_results=True,
                    )
                    try:
                        report.append(
                            f"[{jobname} {job.jobid} {job.creation_time} {job.phase}]"
                        )
                        # Check consistency of dates (destruction_time > end_time > start_time > creation_time)
                        creation_time = (
                            None
                            if not job.creation_time
                            else dt.datetime.strptime(job.creation_time, DT_FMT)
                        )
                        start_time = (
                            None
                            if not job.start_time
                            else dt.datetime.strptime(job.start_time, DT_FMT)
                        )
                        end_time = (
                            None
                            if not job.end_time
                            else dt.datetime.strptime(job.end_time, DT_FMT)
                        )
                        destruction_time = (
                            None
                            if not job.destruction_time
                            else dt.datetime.strptime(job.destruction_time, DT_FMT)
                        )
                        if creation_time and start_time and (creation_time > start_time):
                            report.append("  creation_time > start_time")
                        if start_time and end_time and (start_time > end_time):
                            report.append("  start_time > end_time")
                        if end_time and destruction_time and (end_time > destruction_time):
                            report.append("  end_time > destruction_time")
                        # Check if start_time is set
                        if not start_time and job.phase not in ["PENDING", "QUEUED"]:
                            report.append("  Start time not set")
                        if not end_time and job.phase in TERMINAL_PHASES:
                            report.append("  End time not set")
                        # Check status if phase is not terminal (or for all jobs?)
                        if job.phase not in TERMINAL_PHASES:
                            report.append("  Job is not in a terminal phase")
                            phase = job.phase
                            new_phase = job.get_status()  # will update the phase from manager
                            if new_phase != phase:
                                report.append(
                                    f"  Status has been updated: {phase} --> {new_phase}"
                                )
                        # If destruction time is passed, delete or archive job
                        if destruction_time and (destruction_time < now):
                            # TODO: effective deletion or archiving of job
                            if settings.USE_ARCHIVED_PHASE:
                                if job.phase in ["COMPLETED", "ABORTED", "ERROR"]:
                                    job.archive()
                                    report.append(
                                        f"  Job has been archived (destruction_time={job.destruction_time})"
                                    )
                                else:
                                    # job.delete()
                                    report.append(
                                        f"  Job has been deleted (destruction_time={job.destruction_time})"
                                    )
                                    pass
                            else:
                                # job.delete()
                                report.append(
                                    f"  Job has been deleted (destruction_time={job.destruction_time})"
                                )
                                pass
                    finally:
                        job.close()
            finally:
                joblist.close()
        report.append("Done\n")
        for line in report:
            logger.warning(line)
    except JobAccessDenied as e:
        for line in report:
            logger.warning(line)
        abort_403(str(e))
    except Exception:
        for line in report:
            logger.warning(line)
        abort_500_except()
    # Response
    response.content_type = "text/plain; charset=UTF-8"
    return "Maintenance report:\n" + "\n".join(report)


# ----------
# Interface with job queue manager
# ----------


@app.post("/handler/job_event")
@is_job_server
def job_event():
    """New events for job with given process_id

    This hook expects POST commands that must come from a referenced job server
    POST should include: jobid=, phase=, error_msg=

    Returns:
        200 OK: text/plain (on success)
        403 Forbidden (if not super_user)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    global logger
    try:
        user = User("job_event", settings.JOB_EVENT_TOKEN.get_secret_value())
        logger = logger_init
        logger.debug(f"with POST={str(request.POST.dict)}")
        if "jobid" in request.POST:
            process_id = request.POST["jobid"]
            # Get job properties from DB based on process_id
            job = Job(
                "",
                process_id,
                user,
                get_attributes=True,
                get_parameters=True,
                get_results=True,
                from_process_id=True,
            )
            try:
                # Update job
                if "phase" in request.POST:
                    cur_phase = job.phase
                    new_phase = request.POST["phase"]
                    msg = ""
                    # If phase=ERROR, add error message if available and change job status
                    if new_phase == "ERROR":
                        msg = request.POST.get("error_msg", "")
                        job.change_status("ERROR", msg)
                        logger.info(f"ERROR reported for job {job.jobname} {job.jobid}")
                    elif new_phase not in [cur_phase]:
                        # Convert phase if needed
                        if new_phase not in PHASES:
                            if new_phase in PHASE_CONVERT:
                                new_msg = PHASE_CONVERT[new_phase]["msg"]
                                new_phase = PHASE_CONVERT[new_phase]["phase"]
                                if new_phase in ["ERROR", "ABORTED"]:
                                    msg = new_msg
                            else:
                                raise UserWarning(
                                    "Unknown new phase "
                                    + new_phase
                                    + " for job "
                                    + job.jobid
                                ) from None
                        # Change job status
                        job.change_status(new_phase, msg)
                        logger.info(
                            f"Phase {cur_phase} --> {new_phase} for job {job.jobname} {job.jobid}"
                        )
                    else:
                        raise UserWarning(f"Phase is already {new_phase}") from None
                else:
                    raise UserWarning(f"Unknown event sent for job {job.jobid}") from None
            finally:
                job.close()
        else:
            raise UserWarning("jobid is not defined in POST") from None
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()
    # Response
    response.content_type = "text/plain; charset=UTF-8"
    return ""


# ----------
# /<jobname>
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>")
def get_joblist(jobname):
    """Get list for <jobname> jobs

    Returns:
        the <jobs> element in the UWS schema, can be empty
        200 OK: text/xml (on success)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname}")
        # UWS v1.1 PHASE keyword
        phase = None
        if "PHASE" in request.query:
            # Allow for multiple PHASE keywords to be sent
            phase = re.split("&?PHASE=", request.query_string)[1:]
        # TODO: UWS v1.1 AFTER keyword
        after = request.query.get("AFTER", None)
        # TODO: UWS v1.1 LAST keyword
        last = request.query.get("LAST", None)
        joblist = JobList(jobname, user, phase=phase, after=after, last=last)
        try:
            xml_out = joblist.to_xml()
        finally:
            joblist.close()
        response.content_type = "text/xml; charset=UTF-8"
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()


@app.post(settings.UWS_SERVER_ENDPOINT + "/<jobname>")
def create_job(jobname):
    """Create a new job

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        400 Bad Request (on ParameterTooLong)
        403 Forbidden (on JobAccessDenied)
        500 Internal Server Error (on error)
    """
    # Create new jobid for new job
    user = set_user()
    try:
        # TODO: Check if form submitted correctly, detect file size overflow?
        # Set new job description from POSTed parameters
        job = Job(jobname, "", user, from_post=request)
        try:
            logger.info(f"{jobname} {job.jobid} CREATED and PENDING")
            # If PHASE=RUN, start job
            if request.forms.get("PHASE") == "RUN":
                job.start()
                logger.info(
                    f"{jobname} {job.jobid} QUEUED with process_id={str(job.process_id)}"
                )
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except ParameterTooLong as e:
        abort_400(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except TooManyJobs:
        abort_500_except(
            msg=f"Maximum number of active jobs reached ({settings.NJOBS_MAX})",
            msg_public=f"Maximum number of active jobs reached ({settings.NJOBS_MAX})",
        )
    except CalledProcessError as e:
        abort_500_except(
            msg="STDERR output:\n" + e.output,
            msg_public="Cannot connect to the computing cluster",
        )
    except Exception:
        abort_500_except()
    # Response
    redirect(settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname + "/" + job.jobid, 303)


# ----------
# /<jobname>/<jobid>
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>")
def get_job(jobname, jobid):
    """Get description for job <jobid>

    Returns:
        the <job> element in the UWS schema
        200 OK: text/xml (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(
            jobname,
            jobid,
            user,
            get_attributes=True,
            get_parameters=True,
            get_results=True,
        )
        try:
            # UWS v1.1 blocking behaviour
            if job.phase in ACTIVE_PHASES:
                client_phase = request.query.get("PHASE", job.phase)
                wait_time = int(request.query.get("WAIT", 0))
                if wait_time > settings.WAIT_TIME_MAX:
                    wait_time = settings.WAIT_TIME_MAX
                if wait_time == -1:
                    wait_time = settings.WAIT_TIME_MAX
                if (client_phase == job.phase) and (wait_time > 0):
                    change_status_signal = signal("job_status")
                    change_status_event = threading.Event()

                    def receiver(sender, **kw):
                        logger.info(
                            "{}: {} is now {}".format(
                                sender, kw.get("sig_jobid"), kw.get("sig_phase")
                            )
                        )
                        # Set event if job changed
                        if (kw.get("sig_jobid") == jobid) and (
                            kw.get("sig_phase") != job.phase
                        ):
                            change_status_event.set()
                            return f"{jobid}: signal received and job updated"
                        return f"{jobid}: signal received but job not concerned"

                    # Connect to signal
                    change_status_signal.connect(receiver)
                    # Wait for signal event
                    logger.info(f"{jobid}: Blocking for {wait_time} seconds")
                    event_is_set = change_status_event.wait(wait_time)
                    logger.info(f"{jobid}: Continue execution")
                    change_status_signal.disconnect(receiver)
                    # Reload job if necessary
                    if event_is_set:
                        job = Job(
                            jobname,
                            jobid,
                            user,
                            get_attributes=True,
                            get_parameters=True,
                            get_results=True,
                        )
        finally:
            job.close()
        # Return job description in UWS format
        xml_out = job.to_xml()
        response.content_type = "text/xml; charset=UTF-8"
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()


@app.delete(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>")
def delete_job(jobname, jobid):
    """Delete job with <jobid>

    Returns:
        303 See other: /<jobname> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Delete job
            job.delete()
        finally:
            job.close()
        logger.info(f"{jobname} {jobid} DELETED")
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except CalledProcessError as e:
        abort_500_except(
            msg="STDERR output:\n" + e.output,
            msg_public="Cannot connect to the computing cluster",
        )
    except Exception:
        abort_500_except()
    # Response
    redirect(settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname, 303)


@app.post(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>")
def post_job(jobname, jobid):
    """Alias for delete_job() if ACTION=DELETE"""
    user = set_user()
    try:
        logger.debug(f"POST: {request.POST.__dict__}")
        logger.info(f"deleting {jobname} {jobid}")
        if request.forms.get("ACTION") == "DELETE":
            # Get job properties from DB
            job = Job(jobname, jobid, user)
            try:
                # Delete job
                job.delete()
            finally:
                job.close()
            logger.info(f"{jobname} {jobid} DELETED")
        else:
            raise UserWarning("ACTION=DELETE is not specified in POST") from None
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except CalledProcessError as e:
        abort_500_except(
            msg="STDERR output:\n" + e.output,
            msg_public="Cannot connect to the computing cluster",
        )
    except Exception:
        abort_500_except()
    redirect(settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname, 303)


# ----------
# /<jobname>/<jobid>/phase
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/phase")
def get_phase(jobname, jobid):
    """Get the phase of job <job-id>

    Returns:
        200 OK: text/plain: one of the fixed strings (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        # logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Return value
            response.content_type = "text/plain; charset=UTF-8"
            return job.phase
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.post(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/phase")
def post_phase(jobname, jobid):
    """Change Phase of job <jobid> --> start or abort job

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        if "PHASE" in request.forms:
            new_phase = request.forms.get("PHASE")
            logger.info(f"PHASE={new_phase} {jobname} {jobid}")
            if new_phase == "RUN":
                # Get job properties from DB
                job = Job(
                    jobname, jobid, user, get_attributes=True, get_parameters=True
                )
                try:
                    # Check if phase is PENDING
                    if job.phase not in ["PENDING"]:
                        raise UserWarning("Job has to be in PENDING phase") from None
                    # Start job
                    job.start()
                finally:
                    job.close()
                logger.info(
                    f"{jobname} {jobid} STARTED with process_id={str(job.process_id)}"
                )
            elif new_phase == "ABORT":
                # Get job properties from DB
                job = Job(
                    jobname,
                    jobid,
                    user,
                    get_attributes=True,
                    get_parameters=True,
                    get_results=True,
                )
                try:
                    # Abort job
                    job.abort()
                finally:
                    job.close()
                logger.info(f"{jobname} {jobid} ABORTED")
            else:
                raise UserWarning("PHASE=" + new_phase + " not expected") from None
        else:
            raise UserWarning("PHASE keyword is not specified in POST") from None
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except CalledProcessError as e:
        abort_500_except(
            msg="STDERR output:\n" + e.output,
            msg_public="Cannot connect to the computing cluster",
        )
    except Exception:
        abort_500_except()
    # Response
    redirect(settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname + "/" + jobid, 303)


# ----------
# /<jobname>/<jobid>/executionduration
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/executionduration")
def get_executionduration(jobname, jobid):
    """Get the maximum execution duration of job <jobid>

    Returns:
        200 OK: text/plain: integer number of seconds (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Return value
            response.content_type = "text/plain; charset=UTF-8"
            return str(job.execution_duration)
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.post(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/executionduration")
def post_executionduration(jobname, jobid):
    """Change the maximum execution duration of job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get value from POST
        if "EXECUTIONDURATION" not in request.forms:
            raise UserWarning("EXECUTIONDURATION keyword required") from None
        new_value = request.forms.get("EXECUTIONDURATION")
        # Check new value
        try:
            new_value = int(new_value)
        except ValueError:
            raise UserWarning(
                "Execution duration must be an integer or a float"
            ) from None
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            if job.phase == "PENDING":
                # Change value
                job.set_attribute("execution_duration", new_value)
                logger.info(f"{jobname} {jobid} set execution_duration={str(new_value)}")
            else:
                raise UserWarning(
                    f'Job "{jobid}" must be in PENDING state (currently {job.phase}) to change execution duration'
                ) from None
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()
    # Response
    redirect(settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname + "/" + jobid, 303)


# ----------
# /<jobname>/<jobid>/destruction
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/destruction")
def get_destruction(jobname, jobid):
    """Get the destruction instant for job <jobid>

    Returns:
        200 OK: text/plain: time in ISO8601 format (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Return value
            response.content_type = "text/plain; charset=UTF-8"
            return job.destruction_time
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.post(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/destruction")
def post_destruction(jobname, jobid):
    """Change the destruction instant for job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get value from POST
        if "DESTRUCTION" not in request.forms:
            raise UserWarning("DESTRUCTION keyword required") from None
        new_value = request.forms.get("DESTRUCTION")
        # Check if ISO8601 format, truncate if unconverted data remains
        try:
            dt.datetime.strptime(new_value, DT_FMT)
        except ValueError as e:
            if len(e.args) > 0 and e.args[0].startswith("unconverted data remains:"):
                new_value = new_value[:19]
            else:
                raise UserWarning(
                    f"Destruction time must be in ISO8601 format ({str(e)})"
                ) from None
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Change value
            # job.set_destruction_time(new_value)
            job.set_attribute("destruction_time", new_value)
        finally:
            job.close()
        logger.info(f"{jobname} {jobid} set destruction_time={new_value}")
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()
    # Response
    redirect(settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname + "/" + jobid, 303)


# ----------
# /<jobname>/<jobid>/error
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/error")
def get_error(jobname, jobid):
    """Get any error message associated with job <jobid>

    Returns:
        any representation appropriate to the implementing service
        200 OK: text/plain: error message (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Return value
            response.content_type = "text/plain; charset=UTF-8"
            return job.error
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/quote
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/quote")
def get_quote(jobname, jobid):
    """Get the Quote for job <jobid>

    Returns:
        200 OK: text/plain: integer number of seconds (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Return value
            response.content_type = "text/plain; charset=UTF-8"
            return str(job.quote)
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/parameters
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/parameters")
def get_parameters(jobname, jobid):
    """Get parameters for job <jobid>

    Returns:
        the <parameters> element in the UWS schema
        200 OK: text/xml (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        try:
            # Return job parameters in UWS format
            xml_out = job.parameters_to_xml()
        finally:
            job.close()
        response.content_type = "text/xml; charset=UTF-8"
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/parameters/<pname>")
def get_parameter(jobname, jobid, pname):
    """Get parameter <param> for job <jobid>

    Returns:
        200 OK: text/plain (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Parameter not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info("param=" + pname + " " + jobname + " " + jobid)
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        try:
            # Check if param exists
            if pname not in job.parameters:
                raise storage.NotFoundWarning(
                    f'Parameter "{pname}" NOT FOUND for job "{jobid}"'
                )
            # Return parameter
            response.content_type = "text/plain; charset=UTF-8"
            return str(job.parameters[pname]["value"])
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.post(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/parameters/<pname>")
def post_parameter(jobname, jobid, pname):
    """Change the parameter value for job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid>/parameters (on success)
        400 Bad Request (on ParameterTooLong)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"pname={pname} {jobname} {jobid}")
        # Get value from POST
        if "VALUE" not in request.forms:
            raise UserWarning("VALUE keyword required") from None
        new_value = request.forms.get("VALUE")
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        try:
            # TODO: Check if new_value format is correct (from JDL?)
            # Change value
            if job.phase == "PENDING":
                job.set_parameter(pname, new_value)
                logger.info(f"{jobname} {jobid} set parameter {pname}={new_value}")
            else:
                raise UserWarning(
                    f'Job "{jobid}" must be in PENDING state (currently {job.phase}) to change parameter'
                ) from None
        finally:
            job.close()
    except ParameterTooLong as e:
        abort_400(str(e))
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except Exception:
        abort_500_except()
    # Response
    redirect(
        settings.BASE_URL + settings.UWS_SERVER_ENDPOINT + "/" + jobname + "/" + jobid + "/parameters",
        303,
    )


# ----------
# /<jobname>/<jobid>/results
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/results")
def get_results(jobname, jobid):
    """Get results for job <jobid>

    Returns:
        the <results> element in the UWS schema
        200 OK: text/xml (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_results=True)
        try:
            # Return job results in UWS format
            xml_out = job.results_to_xml()
        finally:
            job.close()
        response.content_type = "text/xml; charset=UTF-8"
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/results/<rname>")
def get_result(jobname, jobid, rname):
    """Get result <rname> for job <jobid>

    Returns:
        200 OK: text/plain (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"rname={rname} {jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_results=True)
        try:
            # Check if result exists
            if rname not in job.results:
                raise storage.NotFoundWarning(
                    f'Result "{rname}" NOT FOUND for job "{jobid}"'
                )
            # Return result
            response.content_type = "text/plain; charset=UTF-8"
            return str(job.results[rname]["url"])
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/stdout")
def get_stdout(jobname, jobid):
    """Get stdout for job <jobid>

    Returns:
        200 OK: file (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        # Get job properties from DB
        # job = Job(jobname, jobid, user, get_results=True)
        logname = "stdout"
        logroot = f"{settings.JOBDATA_PATH}/{jobid}"
        if not os.path.isfile(os.path.join(logroot, logname + ".log")):
            # TODO: get from manager if not available, only available when EXECUTING
            raise storage.NotFoundWarning(
                f'Log "{logname}" NOT FOUND for job "{jobid}"'
            )
        # Return file
        return static_file(logname + ".log", root=logroot, mimetype="text")
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/stderr")
def get_stderr(jobname, jobid):
    """Get stderr for job <jobid>

    Returns:
        200 OK: file (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        # Get job properties from DB
        # job = Job(jobname, jobid, user, get_results=True)
        logname = "stderr"
        logroot = f"{settings.JOBDATA_PATH}/{jobid}"
        if not os.path.isfile(os.path.join(logroot, logname + ".log")):
            # TODO: get from manager if not available, only available when EXECUTING
            raise storage.NotFoundWarning(
                f'Log "{logname}" NOT FOUND for job "{jobid}"'
            )
        # Return file
        return static_file(logname + ".log", root=logroot, mimetype="text")
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/prov<provtype>")
def get_prov(jobname, jobid, provtype):
    """Get prov for job <jobid>

    Returns:
        200 OK: file (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        # Get job properties from DB
        # job = Job(jobname, jobid, user, get_results=True)
        provname = "provenance." + provtype
        provroot = f"{settings.JOBDATA_PATH}/{jobid}"
        if not os.path.isfile(os.path.join(provroot, provname)):
            raise storage.NotFoundWarning(
                f'Prov file "{provname}" NOT FOUND for job "{jobid}"'
            )
        # Return file
        content_types = {
            "json": "application/json",
            "xml": "text/xml",
            "svg": "image/svg+xml",
        }
        return static_file(provname, root=provroot, mimetype=content_types[provtype])
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/owner
# ----------


@app.route(settings.UWS_SERVER_ENDPOINT + "/<jobname>/<jobid>/owner")
def get_owner(jobname, jobid):
    """Get the owner of the job <jobid>

    Returns:
        200 OK: text/plain: an appropriate identifier as discussed in 3 (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info(f"{jobname} {jobid}")
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        try:
            # Return value
            response.content_type = "text/plain; charset=UTF-8"
            return job.owner
        finally:
            job.close()
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except Exception:
        abort_500_except()


# ----------
# run server
# ----------


if __name__ == "__main__":
    # Run local web server
    run(app, host="localhost", port=8082, debug=False, reloader=True)
