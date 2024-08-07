#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
"""

import requests
import traceback
import glob
import re
import io
import sys
import copy
import smtplib
from email.mime.text import MIMEText
import threading
from subprocess import CalledProcessError
from bottle import Bottle, request, response, abort, redirect, run, static_file

from .uws_classes import *
# Note: this import will also import .settings

# Create a new application
app = Bottle()


# ----------
# Set user
# ----------

# Handling the OPTIONS method
# https://github.com/bottlepy/bottle/issues/402
@app.route('/<:re:.*>', method='OPTIONS')
def options_request():
    #response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Headers', 'Authorization, X-Requested-With')
    #pass


#@app.hook('after_request')
#def enableCORSAfterRequestHook():
#    response.set_header('Access-Control-Allow-Origin', '*')


#@hook('after_request')
#def enable_cors():
#    response.headers['Access-Control-Allow-Origin'] = '*'


@app.hook('before_request')
def strip_path():
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


#@app.hook('before_request')
def set_user(jobname=None):
    global logger
    """Set user from request header"""
    # Use anonymous as default
    user_name = 'anonymous'
    user_token = 'anonymous'
    user = User(user_name, user_token)
    # Check if REMOTE_USER is set by web server or use Basic Auth from header
    if request.auth:
        user_name, user_token = request.auth
        if not user_token:
            user_token = 'remote_user'
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
    logger = CustomAdapter(logger_init, {'username': user.name})
    if user == User('anonymous', 'anonymous') and ALLOW_ANONYMOUS == False:
        abort_403('User anomymous not allowed on this server')
    # Add user if not in db
    job_storage = getattr(storage, STORAGE + 'JobStorage')()
    job_storage.add_user(user.name, token=user.token)
    return user


def get_real_ip():
    # logger.debug(request.remote_addr)
    # logger.debug(request.environ.get('HTTP_X_REAL_IP'))
    # logger.debug(request.environ.get('HTTP_X_FORWARDED_FOR'))
    ip = request.environ.get('HTTP_X_REAL_IP', request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr))
    return ip


def is_job_server(func):
    """Test if request comes from a job server"""
    def is_job_server_wrapper(*args, **kwargs):
        # IP or part of an IP has to be in the JOB_SERVERS list
        ip = get_real_ip()
        matching = [x for x in JOB_SERVERS if x in ip]
        if matching:
            logger.info('Access authorized to {} for {} ({})'.format(request.urlparts.path, ip, JOB_SERVERS[matching[0]]))
            pass
        else:
            abort_403('{} is not a job server'.format(ip, request.urlparts.path))
        return func(*args, **kwargs)
    return is_job_server_wrapper


def is_client_trusted(func):
    """Test if request comes from a trusted client"""
    def is_client_trusted_wrapper(*args, **kwargs):
        # IP or part of an IP has to be in the TRUSTED_CLIENTS list
        ip = get_real_ip()
        matching = [x for x in TRUSTED_CLIENTS if x in ip]
        if matching:
            logger.info('Access authorized to {} for {} ({})'.format(request.urlparts.path, ip, TRUSTED_CLIENTS[
                matching[0]]))
            pass
        else:
            abort_403('{} is not a trusted client'.format(ip, request.urlparts.path))
        return func(*args, **kwargs)
    return is_client_trusted_wrapper


def is_localhost(func):
    """Test if localhost"""
    def is_localhost_wrapper(*args, **kwargs):
        ip = get_real_ip()
        if ip != BASE_IP and ip != '::1' and ip != '127.0.0.1':
            abort_403('{} is not localhost'.format(ip, request.urlparts.path))
        return func(*args, **kwargs)
    return is_localhost_wrapper


def is_admin(func):
    """ Decorator to test if user is the admin
    :param func:
    :return:
    """
    def is_admin_wrapper(*args, **kwargs):
        user = set_user()
        if not user.check_admin():
            abort_403('{} is not an admin'.format(user.name, request.urlparts.path))
        return func(*args, **kwargs)
    return is_admin_wrapper


# ----------
# Abort functions
# ----------

class BadRequest(Exception):
    pass


def abort_400(msg=''):
    """HTTP Error 403

    Returns:
        403 Forbidden
    """
    logger.warning('Bad Request: {} ({})'.format(msg, request.urlparts.path))
    abort(400, '{}'.format(msg))


def abort_403(msg=''):
    """HTTP Error 403

    Returns:
        403 Forbidden
    """
    logger.warning('Forbidden: {} ({})'.format(msg, request.urlparts.path))
    abort(403, '{}'.format(msg))
    # abort(403, 'You don\'t have permission to access {} on this server. \n{}'
    #            ''.format(request.urlparts.path, msg))


def abort_404(msg=None):
    """HTTP Error 404

    Returns:
        404 Not Found
        404 Not Found + message
    """
    if msg:
        logger.warning('Not Found: {} ({})'.format(msg, request.urlparts.path))
        abort(404, msg)
    else:
        logger.warning('Not Found')
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
        logger.warning('Internal Server Error')
        abort(500)


def abort_500_except(msg=None, msg_public=None):
    """Show exception and traceback on web page if DEBUG=true

    Returns:
        500 Internal Server Error
        500 Internal Server Error + traceback (on DEBUG=true)
    """
    # message = "{0}: {1!r}".format(type().__name__, ex.args)
    exc_info = sys.exc_info()
    tb = traceback.format_exception(*exc_info)
    message = ''.join(tb)
    if msg:
        message += msg
    logger.error('\n' + message)
    if DEBUG:
        abort(500, message)
    else:
        if not msg_public:
            msg_public = 'Internal Server Error'
        abort(500, msg_public)


# ----------
# Helper functions
# ----------


@app.route('/')
def home():
    # TODO: server and client may have different URLS...
    logger.info("Access to home page")
    logger.info("  Python sys.version: " + sys.version.replace("\n"," "))
    logger.info("  Python sys.exec_prefix: " + sys.exec_prefix)
    resp_status_code = 0
    try:
        client_url = UWS_CLIENT_ENDPOINT
        if not "http" in client_url:
            client_url = BASE_URL + UWS_CLIENT_ENDPOINT
        resp = requests.get(client_url)
        resp_status_code = resp.status_code
    except Exception as e:
        msg_txt = "Client is not responding"
        logger.warning(msg_txt)
        logger.warning(repr(e))
    if resp_status_code == 200:
        logger.info("Redirect to client: " + client_url)
        redirect(client_url)
    return 'OPUS - https://opus-job-manager.readthedocs.io'


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root=APP_PATH)


def send_mail(send_to, subject, msg):
    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        # server.starttls()
        # server.login("YOUR EMAIL ADDRESS", "YOUR PASSWORD")
        mail_text = MIMEText(msg, 'plain')
        mail_text['Subject'] = subject
        mail_text['From'] = SENDER_EMAIL
        mail_text['To'] = send_to
        server.sendmail(SENDER_EMAIL, send_to, mail_text.as_string())
        server.quit()
    except Exception:
        logger.error('Unable to send email')
        abort_500('Unable to send email')

# ----------
# SCIM v2 API for user management
# ----------


@app.get('/scim/v2/ServiceProviderConfig')
def SCIM_ServiceProviderConfig():
    scim_config = """
  {
    "schemas":
      ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
    "patch": {
      "supported":false
    },
    "bulk": {
      "supported":false,
      "maxOperations":1000,
      "maxPayloadSize":1048576
    },
    "filter": {
      "supported":false,
      "maxResults": 200
    },
    "changePassword": {
      "supported":false
    },
    "sort": {
      "supported":false
    },
    "etag": {
      "supported":false
    },
    "authenticationSchemes": [
      {
        "name": "HTTP Basic",
        "description":
          "Authentication scheme using the HTTP Basic Standard",
        "specUri": "http://www.rfc-editor.org/info/rfc2617",
        "type": "httpbasic"
       }
    ]
  }
    """
    response.content_type = 'application/json; charset=UTF-8'
    return scim_config


@app.get('/scim/v2/Schemas')
def SCIM_Schemas():
    scim_schemas = """
  {
    "id" : "urn:ietf:params:scim:schemas:core:2.0:User",
    "name" : "User",
    "description" : "User Account",
    "attributes" : [
      {
        "name" : "userName",
        "type" : "string",
        "multiValued" : false,
        "description" : "Unique identifier for the User, typically used by the user to directly authenticate to the service provider. Each User MUST include a non-empty userName value.  This identifier MUST be unique across the service provider's entire set of Users. REQUIRED.",
        "required" : true,
        "caseExact" : false,
        "mutability" : "readWrite",
        "returned" : "default",
        "uniqueness" : "server"
      },
      {
        "name" : "token",
        "type" : "string",
        "multiValued" : false,
        "description" : "The User's token.",
        "required" : true,
        "caseExact" : true,
        "mutability" : "writeOnly",
        "returned" : "never",
        "uniqueness" : "none"
      },
      {
        "name" : "roles",
        "type" : "string",
        "multiValued" : true,
        "description" : "A coma-separated list of roles for the User",
        "required" : false,
        "mutability" : "readWrite",
        "returned" : "default"
      },
      {
        "name" : "active",
        "type" : "boolean",
        "multiValued" : false,
        "description" : "A Boolean value indicating the User's administrative status.",
        "required" : false,
        "mutability" : "readWrite",
        "returned" : "default"
      }
    ]
  }
    """
    response.content_type = 'application/json; charset=UTF-8'
    return scim_schemas


@app.get('/scim/v2/ResourceTypes')
def SCIM_ResourceTypes():
    scim_resourcetypes = """
{
  "itemsPerPage": 1,
  "startIndex": 1,
  "Resources": [
    {
      "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
      "id": "Users",
      "name": "User",
      "endpoint": "/Users",
      "description": "User Account",
      "schema": "urn:scim:schemas:core:2.0:User"
    }
  ]
}
    """
    response.content_type = 'application/json; charset=UTF-8'
    return scim_resourcetypes


@app.get('/scim/v2/ResourceTypes/User')
def SCIM_ResourceTypes_User():
    scim_resourcetypes = """
    {
      "id": "Users",
      "schemas": [
        "urn:scim:schemas:core:2.0:ResourceType"
      ],
      "name": "User",
      "description": "Core User",
      "endpoint": "/Users",
      "schema": "urn:scim:schemas:core:2.0:User"
    }
    """
    response.content_type = 'application/json; charset=UTF-8'
    return scim_resourcetypes


def user2scim(u):
    user_dict = {
        'schemas': ["urn:scim:schemas:core:2.0:User"],
        'id': u['name'],
        'userName': u['name'],
        'meta': {
            "resourceType": "User",
            "created": str(u['first_connection']),
            "lastModified": str(u['first_connection']),
            "location": "scim/v2/Users/" + u['name'],
        }
    }
    for attr in ['token', 'roles', 'active']:
        user_dict[attr] = u[attr]
    return user_dict


@app.get('/scim/v2/Users')
@is_client_trusted
@is_admin
def get_users():
    job_storage = getattr(storage, STORAGE + 'JobStorage')()
    users = job_storage.get_users()
    scim_user_resources = []
    for u in users:
        # do not expose opus-admin
        if u['name'] != ADMIN_NAME:
            scim_user_resources.append(user2scim(u))
    scim_users = {
        "itemsPerPage": 10000,
        "startIndex": 1,
        "Resources": scim_user_resources
    }
    return scim_users


@app.post('/scim/v2/Users')
@is_client_trusted
@is_admin
def create_user():
    name = request.POST.get('name', '')
    if name:
        token = request.POST.get('token', '')
        roles = request.POST.get('roles', None)
        job_storage = getattr(storage, STORAGE + 'JobStorage')()
        job_storage.add_user(name, token=token, roles=roles)
        users = job_storage.get_users(name=name)
        u = users[0]
        logger.info('User created: ' + name)
        return user2scim(u)
    else:
        abort_500('No user name provided')


@app.get('/scim/v2/Users/<name>')
@is_client_trusted
@is_admin
def get_user(name):
    job_storage = getattr(storage, STORAGE + 'JobStorage')()
    users = job_storage.get_users(name=name)
    u = users[0]
    return user2scim(u)


@app.route('/scim/v2/Users/<name>', method='POST')
@is_client_trusted
@is_admin
def patch_user(name):
    job_storage = getattr(storage, STORAGE + 'JobStorage')()
    users = job_storage.get_users(name=name)
    u = users[0]
    for k in request.POST.keys():
        if k in ['token', 'roles', 'active']:
            u[k] = request.POST[k]
            # save modified user
            job_storage.update_user(name, k, request.POST[k])
            logger.info('User patched: ' + name)
    return user2scim(u)


@app.route('/scim/v2/Users/<name>', method='DELETE')
@is_client_trusted
@is_admin
def delete_user(name):
    job_storage = getattr(storage, STORAGE + 'JobStorage')()
    users = job_storage.remove_user(name)
    logger.info('User deleted: ' + name)
    response.content_type = 'text/plain; charset=UTF-8'
    response.status = 200
    return 'Success'


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


@app.get('/jdl')
def get_jobnames():
    """
    Get list of available jobs on server
    :return: list of job names in json
    """
    user = set_user()
    try:
        # jobnames = ['copy', 'ctbin']
        # List jdl files (=available jobs)
        jdl = getattr(uws_jdl, JDL)()
        jobnames_all = jdl.get_jobnames()
        jobnames = []
        if not CHECK_PERMISSIONS or user.check_admin():
            jobnames = jobnames_all
        else:
            # keep jobnames accessible to user
            #db = storage.__dict__[STORAGE + 'JobStorage']()
            db = getattr(storage, STORAGE + 'JobStorage')()
            roles = db.get_roles(user)
            jobnames = [j for j in jobnames_all if j in roles]
        jobnames.sort()
        details = {}
        for j in jobnames:
            # Get JDL
            jdl.read(j)
            # map some information
            details[j] = copy.copy(jdl.content)
        jobnames_json = {'jobnames': jobnames, 'details': details}
        return jobnames_json
    except UserWarning as e:
        abort_404(e.args[0])


#@app.post('/config/job_definition')
@app.post('/jdl')
@is_client_trusted
def create_new_job_definition():
    """Use posted parameters to create a new JDL file for the given job"""
    # No need to authenticate, users can propose new jobs that will have to be validated
    # Check if client is trusted? not really needed
    jobname = ''
    user = set_user()
    try:
        jobname = request.forms.get('name').split('/')[-1]
        if jobname:
            # Create JDL file from job_jdl
            #jdl = uws_jdl.__dict__[JDL]()
            jdl = getattr(uws_jdl, JDL)()
            jdl.set_from_post(request.forms, user)
            # Save as a new job description
            jdl.save('tmp/' + jobname)
        else:
            abort_500('No jobname given')
    except:
        abort_500_except()
    # Response
    return {'jobname': jobname}


@app.post('/jdl/import_jdl')
@is_client_trusted
def import_job_definition():
    """Use posted parameters to create a new JDL file for the given job"""
    # No need to authenticate, users can propose new jobs that will have to be validated
    # Check if client is trusted? not really needed
    jobname = ''
    user = set_user()
    try:
        # Save JDL file as new for this jobname
        f = request.files.get('jdl_file', None)
        if f:
            #now = dt.datetime.now().isoformat().split('.')[0]
            # Get jobname from file name (?)
            jdl = getattr(uws_jdl, JDL)()
            jobname = f.filename.split(jdl.extension)[0]  # e.g. remove _vot.xml at the end of filename
            if jobname == f.filename:  # else remove extension
                jobname = os.path.splitext(os.path.basename(f.filename))[0]
            if jobname:
                logger.debug(jobname)
                fname_temp = jdl._get_filename('tmp/' + jobname)
                logger.debug(fname_temp)
                if os.path.isfile(fname_temp):
                    os.remove(fname_temp)
                f.save(fname_temp)
                # Read JDL
                logger.debug('tmp/' + jobname)
                jdl.read('tmp/' + jobname)
                if jdl.content['name']:
                    if jdl.content['name'] != jobname:
                        logger.warning('Jobname and filename not matching, JDL renamed: {} ({})'.format(
                            jdl.content['name'], f.filename))
                        jobname = jdl.content['name']
                        fname_mv = jdl._get_filename('tmp/' + jobname)
                        shutil.move(fname_temp, fname_mv)
                else:
                    logger.warning('No jobname found, using filename to define jobname: {} ({})'.format(
                        jobname, f.filename))
                    jdl.content['name'] = jobname
                # Save JDL
                jdl.save('tmp/' + jobname)
            else:
                abort_500('No jobname found for file ' + f.filename)
    except:
        abort_500_except()
    # Return code 200 and jobname
    return {'jobname': jobname}
    # redirect('/client/job_definition?jobname={}&msg=validated'.format(jobname), 303)


@app.post('/jdl/tmp/<jobname>/validation_request')
@is_client_trusted
def validation_request_job_definition(jobname):
    """Use filled form to create a JDL file for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    user = set_user()
    try:
        jdl = getattr(uws_jdl, JDL)()
        jdl_src = '{}/tmp/{}{}'.format(jdl.jdl_path, jobname, jdl.extension)
        if os.path.isfile(jdl_src):
            # send email to admin
            # mail.
            mail_subject = 'OPUS job validation request: {}'.format(jobname)
            mail_text = '{}\n{}/jdl/tmp/{}/json\n(from: {})'.format(mail_subject, BASE_URL, jobname, user.name)
            send_mail(ADMIN_EMAIL, mail_subject, mail_text)
            logger.info('Validation request sent to admin: ' + jobname)
        else:
            logger.info('No JDL  found for validation: ' + jdl_src)
            abort_500('No JDL file found for ' + jobname)
    except:
        abort_500_except()
    # Return code 200
    return {'jobname': jobname}


#@app.get('/config/validate_job/<jobname>')
@app.post('/jdl/tmp/<jobname>/validate')
@is_client_trusted
@is_admin
def validate_job_definition(jobname):
    """Use filled form to create a JDL file for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    try:
        # Copy script and jdl from new
        # jdl = uws_jdl.__dict__[JDL]()
        jdl = getattr(uws_jdl, JDL)()
        jdl_src = '{}/tmp/{}{}'.format(jdl.jdl_path, jobname, jdl.extension)
        jdl_dst = '{}/{}{}'.format(jdl.jdl_path, jobname, jdl.extension)
        script_src = '{}/tmp/{}.sh'.format(jdl.scripts_path, jobname)
        script_dst = '{}/{}.sh'.format(jdl.scripts_path, jobname)
        # Save, then copy from tmp/
        if os.path.isfile(jdl_src):
            if os.path.isfile(jdl_dst):
                # Save file with version and time stamp
                mt = dt.datetime.fromtimestamp(os.path.getmtime(jdl_dst)).isoformat().split('.')[0]
                jdl.read(jobname)  # need version for saved files
                jdl_dst_save = '{}/saved/{}_v{}_{}{}'.format(
                    jdl.jdl_path, jobname, jdl.content['version'], mt, jdl.extension)
                os.rename(jdl_dst, jdl_dst_save)
                logger.info('Previous job JDL saved: ' + jdl_dst_save)
            shutil.copy(jdl_src, jdl_dst)
            logger.info('Job JDL file copied: ' + jdl_dst)
        else:
            logger.info('No JDL  found for validation: ' + jdl_src)
            abort_500('No JDL file found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
        if os.path.isfile(script_src):
            if os.path.isfile(script_dst):
                # Save file with time stamp
                mt = dt.datetime.fromtimestamp(os.path.getmtime(script_dst)).isoformat().split('.')[0]
                jdl.read(jobname)  # need version for saved files
                script_dst_save = '{}/saved/{}_v{}_{}.sh'.format(
                    SCRIPTS_PATH, jobname, jdl.content['version'], mt)
                os.rename(script_dst, script_dst_save)
                logger.info('Previous job script saved: ' + script_dst_save)
            shutil.copy(script_src, script_dst)
            logger.info('Job script copied: ' + script_dst)
            # Copy script to job manager
            #manager = managers.__dict__[MANAGER + 'Manager']()
            manager = getattr(managers, MANAGER + 'Manager')()
            manager.cp_script(jobname)
            logger.info('Job script copied to work cluster: ' + jobname)
        else:
            logger.info('No job script found for validation: ' + script_src)
            abort_500('No job script found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except:
        abort_500_except()
    # Return code 200
    return {'jobname': jobname}
    # redirect('/client/job_definition?jobname={}&msg=validated'.format(jobname), 303)


@app.get('/jdl/<jobname:path>/convert')
@is_client_trusted
@is_admin
def convert_jdl(jobname):
    """
    Get json description file for jobname
    :param jobname:
    :return: json description
    """
    try:
        #logger.info(jobname)
        uws_jdl.update_vot(jobname)
    except UserWarning as e:
        abort_404(e.args[0])
    except:
        abort_500_except()
    return 'JDL converted for {}'.format(jobname)


#@app.get('/config/cp_script/<jobname>')
@app.post('/jdl/<jobname:path>/copy_script')
@is_client_trusted
@is_admin
def cp_script(jobname):
    """copy script to job manager for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    try:
        # Copy script to job manager
        script_dst = '{}/{}.sh'.format(SCRIPTS_PATH, jobname)
        if os.path.isfile(script_dst):
            #manager = managers.__dict__[MANAGER + 'Manager']()
            manager = getattr(managers, MANAGER + 'Manager')()
            manager.cp_script(jobname)
            logger.info('Job script copied to work cluster: ' + jobname)
        else:
            logger.info('No job script found for job: ' + jobname)
            abort_500('No job script found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except:
        abort_500_except()
    # Return code 200
    response.content_type = 'text/plain; charset=UTF-8'
    return 'Script copied for job {}'.format(jobname)
    # redirect('/client/job_definition?jobname={}&msg=script_copied'.format(jobname), 303)


@app.get('/jdl/<jobname:path>/script')
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
        db = getattr(storage, STORAGE + 'JobStorage')()
        if not CHECK_PERMISSIONS or db.has_access(user, jobname):
            # Get JDL content
            jdl = getattr(uws_jdl, JDL)()
            jdl.read_script(jobname)
            logger.info('Job script downloaded: {}'.format(jobname))
            response.content_type = 'text/plain; charset=UTF-8'
            return jdl.content['script']
        else:
            abort_403()
    except UserWarning as e:
        abort_404(e.args[0])
    except:
        abort_500_except()


@app.get('/jdl/<jobname:path>/json')
def get_jdl_json(jobname):
    """
    Get json description file for jobname
    :param jobname:
    :return: json description
    """
    user = set_user()
    try:
        db = getattr(storage, STORAGE + 'JobStorage')()
        # if not CHECK_PERMISSIONS or db.has_access(user, jobname) or 'tmp/' in jobname:
        # Get JDL content
        jdl = getattr(uws_jdl, JDL)()
        jdl.read(jobname)
        logger.debug('JDL downloaded ad JSON: {}'.format(jobname))
        return jdl.content
        # else:
        #     abort_403()
    except UserWarning as e:
        abort_404(e.args[0])
    except:
        abort_500_except()


@app.get('/jdl/<jobname>')
def get_jdl(jobname):
    """
    Get JDL file for jobname
    :param jobname:
    :return: VOTable file
    """
    #logger.info(jobname)
    user = set_user()
    try:
        db = getattr(storage, STORAGE + 'JobStorage')()
        # if not CHECK_PERMISSIONS or db.has_access(user, jobname):
        # Get JDL content
        jdl = getattr(uws_jdl, JDL)()
        fname = jdl._get_filename(jobname)
        download_dir, download_fname = os.path.split(fname)
        logger.debug(download_fname)
        if os.path.isfile(fname):
            with open(fname) as f:
                jdl = f.readlines()
            logger.debug('JDL file downloaded: {}'.format(fname))
            return static_file(download_fname, root=download_dir, download=download_fname)
            #response.content_type = 'text/xml; charset=UTF-8'
            #return jdl
        else:
            abort_404('No VOTable file found for ' + jobname)
        # else:
        #     abort_403()
    except UserWarning as e:
        abort_404(e.args[0])
    except:
        abort_500_except()


@app.delete('/jdl/<jobname>')
@is_client_trusted
@is_admin
def delete_jdl(jobname):
    """
    Delete jdl with
    :param jobname:
    :return:
    """
    try:
        jdl = getattr(uws_jdl, JDL)()
        jdl.read(jobname)  # need version for saved files
        jdl_src = '{}/{}{}'.format(jdl.jdl_path, jobname, jdl.extension)
        script_src = '{}/{}.sh'.format(jdl.scripts_path, jobname)
        if os.path.isfile(jdl_src):
            # Save file with version and time stamp
            mt = dt.datetime.fromtimestamp(os.path.getmtime(jdl_src)).isoformat().split('.')[0]
            jdl_dst_save = '{}/saved/{}_v{}_{}_DELETED{}'.format(
                jdl.jdl_path, jobname, jdl.content['version'], mt, jdl.extension)
            shutil.move(jdl_src, jdl_dst_save)
            logger.info('JDL file archived and deleted: ' + jdl_dst_save)
        else:
            logger.warning('No JDL file found: ' + jdl_src)
            abort_500('No JDL file found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
        if os.path.isfile(script_src):
            # Save file with time stamp
            mt = dt.datetime.fromtimestamp(os.path.getmtime(script_src)).isoformat().split('.')[0]
            script_dst_save = '{}/saved/{}_v{}_{}_DELETED.sh'.format(
                SCRIPTS_PATH, jobname, jdl.content['version'], mt)
            shutil.move(script_src, script_dst_save)
            logger.info('Job script archived and deleted: ' + script_dst_save)
        else:
            logger.warning('No job script found: ' + script_src)
            abort_500('No job script found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except:
        abort_500_except()
    # Return code 200
    return {'jobname': jobname}


# ----------
# Results and provenance
# ----------


@app.route('/store/<eid>/<fname>')
def get_result_file(eid, fname):
    redirect(BASE_URL + '/store?ID=' + eid, 303)


@app.route('/store')
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
        if not 'ID' in request.query:
            raise UserWarning('"ID" is not specified in request')
        entity_id = request.query['ID']
        # logger.debug('Init storage for entity {}'.format(entity_id))
        job_storage = getattr(storage, STORAGE + 'JobStorage')()
        entity = job_storage.get_entity(entity_id)

        if CHECK_OWNER:
            if user in special_users:
                pass
            else:
                if entity['owner'] == user.name:
                    pass
                else:
                    raise EntityAccessDenied('User {} is not the owner of the entity'.format(user.name))

        download = entity['entity_id'] + '_' + entity['file_name'] #  + os.path.splitext(entity['file_name'])[1]
        logger.debug('{}'.format(str(entity)))
        response.set_header('Content-type', entity['content_type'])
        return static_file(entity['file_name'], root=entity['file_dir'], mimetype=entity['content_type'],
                           download=download)
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
    except:
        abort_500_except()


# TODO: function will be deprecated (replaced by /store)
@app.route('/store_old/<jobid>/<rname>')  # /<rfname>')
def get_result_file(jobid, rname):  # , rfname):
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
        job = Job('', jobid, user, get_attributes=False, get_results=True)
        # Check if result exists
        if rname not in job.results:
            raise storage.NotFoundWarning('Result "{}" NOT FOUND for job "{}"'.format(rname, jobid))
        # Return result
        result_details = {
            'stdout': 'stdout.log',
            'stderr': 'stderr.log',
            'provjson': 'provenance.json',
            'provxml': 'provenance.xml',
            'provsvg': 'provenance.svg',
        }
        if rname in result_details:
            rfname = result_details[rname]
        else:
            rfname = job.get_result_filename(rname)
        if rname in ['stdout', 'stderr']:
            return static_file(rfname, root='{}/{}'.format(JOBDATA_PATH, job.jobid),
                               mimetype='text')
        #response.content_type = 'text/plain; charset=UTF-8'
        #return str(job.results[result]['url'])
        content_type = job.results[rname]['content_type']
        logger.debug('{} {} {} {} {}'.format(job.jobname, jobid, rname, rfname, content_type))
        response.set_header('Content-type', content_type)
        if any(x in content_type for x in ['text', 'xml', 'json', 'image/png', 'image/jpeg']):
            return static_file(rfname, root='{}/{}'.format(RESULTS_PATH, job.jobid),
                               mimetype=content_type)
        else:
            response.set_header('Content-Disposition', 'attachment; filename="{}"'.format(rfname))
            return static_file(rfname, root='{}/{}'.format(RESULTS_PATH, job.jobid),
                               mimetype=content_type, download=True)
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.get('/provsap')
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
        if not 'ID' in request.query:
            raise UserWarning('"ID" is not specified in request')
        kwargs = {}
        kwargs['depth'] = request.query.get('DEPTH', 1)
        kwargs['model'] = request.query.get('MODEL', 'IVOA')
        kwargs['direction'] = request.query.get('DIRECTION', 'BACK')
        kwargs['agents'] = int(request.query.get('AGENTS', 1))
        kwargs['members'] = int(request.query.get('MEMBERS', 0))
        kwargs['descriptions'] = int(request.query.get('DESCRIPTIONS', 0))
        kwargs['configuration'] = int(request.query.get('CONFIGURATION', 1))
        respformat = request.query.get('RESPONSEFORMAT', 'PROV-SVG')
        attributes = int(request.query.get('ATTRIBUTES', 1))
        gd = request.query.get('GD', 'LR')
        if kwargs['depth'] == 'ALL':
            kwargs['depth'] = -1
        else:
            kwargs['depth'] = int(kwargs['depth'])
        ids = request.query.getall('ID')
        pdocs = []
        for id in ids:
            show_generated = True
            # Test if ID is an entity_id, and get the related jobid (that generated the entity)
            job_storage = getattr(storage, STORAGE + 'JobStorage')()
            entity = job_storage.get_entity(id, silent=True)
            if entity:
                jobid = entity.get('jobid')
                show_generated = True
                if kwargs['depth'] > 0:
                    kwargs['depth'] -= 1
            else:
                # Then it must be a jobid
                jobid = id
            # Get job properties from DB
            #job = Job('', jobid, user, get_attributes=True, get_parameters=True, get_results=True)
            #logger.info('{} {}'.format(job.jobname, jobid))
            # Return job provenance
            logger.debug('{}'.format(kwargs))
            pdoc = provenance.job2prov(jobid, user, show_generated=show_generated, **kwargs)
            pdocs.append(pdoc)
        # Merge all pdocs
        pdoc = pdocs.pop()
        for opdoc in pdocs:
            pdoc.update(opdoc)
        pdoc.unified()

        filename_base = "provsap_" + "_".join(ids)
        if respformat == 'PROV-SVG':
            svg_content = provenance.prov2svg_content(pdoc, attributes=attributes, direction=gd)
            response.content_type = 'text/xml'
            response.headers[u"Content-Disposition"] = u'filename="' + filename_base + '.svg"'
            return svg_content
        elif respformat == 'PROV-PNG':
            png_content = provenance.prov2png_content(pdoc, attributes=attributes, direction=gd)
            response.content_type = 'image/png'
            response.headers[u"Content-Disposition"] = u'filename="' + filename_base + '.png"'
            return png_content
        elif respformat == 'PROV-XML':
            result = io.BytesIO()
            pdoc.serialize(result, format='xml')
            result.seek(0)
            response.content_type = 'text/xml; charset=UTF-8'
            response.headers[u"Content-Disposition"] = u'filename="' + filename_base + '.xml"'
            return b'\n'.join(result.readlines())
        elif respformat == 'PROV-JSON':  # return PROV-JSON as default
            result = io.BytesIO()
            pdoc.serialize(result, format='json')
            result.seek(0)
            response.content_type = 'application/json; charset=UTF-8'
            response.headers[u"Content-Disposition"] = u'filename="' + filename_base + '.json"'
            return b'\n'.join(result.readlines())
        else:
            raise BadRequest('Bad value for RESPONSEFORMAT ({}).\nAvailable values are (\'PROV-JSON\', \'PROV-XML\', \'PROV-SVG\').'.format(format))
    except BadRequest as e:
        abort_400(e.args[0])
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


# ----------
# Server maintenance
# ----------


@app.route('/handler/maintenance/<jobname>')
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
        user = User('maintenance', MAINTENANCE_TOKEN)
        logger = logger_init
        if jobname != "__all__":
            jobnames = [jobname]
        else:
            jdl = getattr(uws_jdl, JDL)()
            jobnames = jdl.get_jobnames()
        for jobname in jobnames:
            report.append('Maintenance checks for {}...'.format(jobname))
            # Get joblist
            joblist = JobList(jobname, user, where_owner=False)
            now = dt.datetime.now()
            for j in joblist.jobs:
                # For each job:
                job = Job(jobname, j['jobid'], user, get_attributes=True, get_parameters=True, get_results=True)
                report.append('[{} {} {} {}]'.format(jobname, job.jobid, job.creation_time, job.phase))
                # Check consistency of dates (destruction_time > end_time > start_time > creation_time)
                creation_time = None if not job.creation_time else dt.datetime.strptime(job.creation_time, DT_FMT)
                start_time = None if not job.start_time else dt.datetime.strptime(job.start_time, DT_FMT)
                end_time = None if not job.end_time else dt.datetime.strptime(job.end_time, DT_FMT)
                destruction_time = None if not job.destruction_time else dt.datetime.strptime(job.destruction_time, DT_FMT)
                if creation_time and start_time and (creation_time > start_time):
                    report.append('  creation_time > start_time')
                if start_time and end_time and (start_time > end_time):
                    report.append('  start_time > end_time')
                if end_time and destruction_time and (end_time > destruction_time):
                    report.append('  end_time > destruction_time')
                # Check if start_time is set
                if not start_time and job.phase not in ['PENDING', 'QUEUED']:
                    report.append('  Start time not set')
                if not end_time and job.phase in TERMINAL_PHASES:
                    report.append('  End time not set')
                # Check status if phase is not terminal (or for all jobs?)
                if job.phase not in TERMINAL_PHASES:
                    report.append('  Job is not in a terminal phase')
                    phase = job.phase
                    new_phase = job.get_status()  # will update the phase from manager
                    if new_phase != phase:
                        report.append('  Status has been updated: {} --> {}'.format(phase, new_phase))
                # If destruction time is passed, delete or archive job
                if destruction_time and (destruction_time < now):
                    # TODO: effective deletion or archiving of job
                    if USE_ARCHIVED_PHASE:
                        if job.phase in ['COMPLETED', 'ABORTED', 'ERROR']:
                            job.archive()
                            report.append(
                                '  Job has been archived (destruction_time={})'.format(job.destruction_time))
                        else:
                            # job.delete()
                            report.append(
                                '  Job has been deleted (destruction_time={})'.format(job.destruction_time))
                            pass
                    else:
                        # job.delete()
                        report.append(
                            '  Job has been deleted (destruction_time={})'.format(job.destruction_time))
                        pass
        report.append('Done\n')
        for line in report:
            logger.warning(line)
    except JobAccessDenied as e:
        for line in report:
            logger.warning(line)
        abort_403(str(e))
    except:
        for line in report:
            logger.warning(line)
        abort_500_except()
    # Response
    response.content_type = 'text/plain; charset=UTF-8'
    return 'Maintenance report:\n' + '\n'.join(report)


# ----------
# Interface with job queue manager
# ----------


@app.post('/handler/job_event')
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
        user = User('job_event', JOB_EVENT_TOKEN)
        logger = logger_init
        logger.debug('with POST={}'.format(str(request.POST.dict)))
        if 'jobid' in request.POST:
            process_id = request.POST['jobid']
            # Get job properties from DB based on process_id
            job = Job('', process_id, user,
                      get_attributes=True, get_parameters=True, get_results=True,
                      from_process_id=True)
            # Update job
            if 'phase' in request.POST:
                cur_phase = job.phase
                new_phase = request.POST['phase']
                msg = ''
                # If phase=ERROR, add error message if available and change job status
                if new_phase == 'ERROR':
                    msg = request.POST.get('error_msg', '')
                    job.change_status('ERROR', msg)
                    logger.info('ERROR reported for job {} {}'.format(job.jobname, job.jobid))
                elif new_phase not in [cur_phase]:
                    # Convert phase if needed
                    if new_phase not in PHASES:
                        if new_phase in PHASE_CONVERT:
                            new_msg = PHASE_CONVERT[new_phase]['msg']
                            new_phase = PHASE_CONVERT[new_phase]['phase']
                            if new_phase in ['ERROR', 'ABORTED']:
                                msg = new_msg
                        else:
                            raise UserWarning('Unknown new phase ' + new_phase + ' for job ' + job.jobid)
                    # Change job status
                    job.change_status(new_phase, msg)
                    logger.info('Phase {} --> {} for job {} {}'
                                ''.format(cur_phase, new_phase, job.jobname, job.jobid))
                else:
                    raise UserWarning('Phase is already ' + new_phase)
            else:
                raise UserWarning('Unknown event sent for job ' + job.jobid)
        else:
            raise UserWarning('jobid is not defined in POST')
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except:
        abort_500_except()
    # Response
    response.content_type = 'text/plain; charset=UTF-8'
    return ''


# ----------
# /<jobname>
# ----------


@app.route('/rest/<jobname>')
def get_joblist(jobname):
    """Get list for <jobname> jobs

    Returns:
        the <jobs> element in the UWS schema, can be empty
        200 OK: text/xml (on success)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{}'.format(jobname))
        # UWS v1.1 PHASE keyword
        phase = None
        if 'PHASE' in request.query:
            # Allow for multiple PHASE keywords to be sent
            phase = re.split('&?PHASE=', request.query_string)[1:]
        # TODO: UWS v1.1 AFTER keyword
        after = request.query.get('AFTER', None)
        # TODO: UWS v1.1 LAST keyword
        last = request.query.get('LAST', None)
        joblist = JobList(jobname, user, phase=phase, after=after, last=last)
        xml_out = joblist.to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except:
        abort_500_except()


@app.post('/rest/<jobname>')
def create_job(jobname):
    """Create a new job

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        500 Internal Server Error (on error)
    """
    # Create new jobid for new job
    user = set_user()
    try:
        # TODO: Check if form submitted correctly, detect file size overflow?
        # Set new job description from POSTed parameters
        job = Job(jobname, '', user, from_post=request)
        logger.info('{} {} CREATED and PENDING'.format(jobname, job.jobid))
        # If PHASE=RUN, start job
        if request.forms.get('PHASE') == 'RUN':
            job.start()
            logger.info('{} {} QUEUED with process_id={}'
                        ''.format(jobname, job.jobid, str(job.process_id)))
    except UserWarning as e:
        abort_500(e.args[0])
    except TooManyJobs as e:
        abort_500(e.args[0])
    except CalledProcessError as e:
        abort_500_except(msg='STDERR output:\n' + e.output, msg_public='Cannot connect to the computing cluster')
    except:
        abort_500_except()
    # Response
    redirect(BASE_URL + '/rest/' + jobname + '/' + job.jobid, 303)


# ----------
# /<jobname>/<jobid>
# ----------


@app.route('/rest/<jobname>/<jobid>')
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
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user,
                  get_attributes=True, get_parameters=True, get_results=True)
        # UWS v1.1 blocking behaviour
        if job.phase in ACTIVE_PHASES:
            client_phase = request.query.get('PHASE', job.phase)
            wait_time = int(request.query.get('WAIT', 0))
            if wait_time > WAIT_TIME_MAX:
                wait_time = WAIT_TIME_MAX
            if wait_time == -1:
                wait_time = WAIT_TIME_MAX
            if (client_phase == job.phase) and (wait_time > 0):
                change_status_signal = signal('job_status')
                change_status_event = threading.Event()

                def receiver(sender, **kw):
                    logger.info('{}: {} is now {}'.format(sender, kw.get('sig_jobid'), kw.get('sig_phase')))
                    # Set event if job changed
                    if (kw.get('sig_jobid') == jobid) and (kw.get('sig_phase') != job.phase):
                        change_status_event.set()
                        return '{}: signal received and job updated'.format(jobid)
                    return '{}: signal received but job not concerned'.format(jobid)

                # Connect to signal
                change_status_signal.connect(receiver)
                # Wait for signal event
                logger.info('{}: Blocking for {} seconds'.format(jobid, wait_time))
                event_is_set = change_status_event.wait(wait_time)
                logger.info('{}: Continue execution'.format(jobid))
                change_status_signal.disconnect(receiver)
                # Reload job if necessary
                if event_is_set:
                    job = Job(jobname, jobid, user,
                              get_attributes=True, get_parameters=True, get_results=True)
        # Return job description in UWS format
        xml_out = job.to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except:
        abort_500_except()


@app.delete('/rest/<jobname>/<jobid>')
def delete_job(jobname, jobid):
    """Delete job with <jobid>

    Returns:
        303 See other: /<jobname> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Delete job
        job.delete()
        logger.info('{} {} DELETED'.format(jobname, jobid))
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except CalledProcessError as e:
        abort_500_except(msg='STDERR output:\n' + e.output, msg_public='Cannot connect to the computing cluster')
    except:
        abort_500_except()
    # Response
    redirect(BASE_URL + '/rest/' + jobname, 303)


@app.post('/rest/<jobname>/<jobid>')
def post_job(jobname, jobid):
    """Alias for delete_job() if ACTION=DELETE"""
    user = set_user()
    try:
        logger.debug('POST: {}'.format(request.POST.__dict__))
        logger.info('deleting {} {}'.format(jobname, jobid))
        if request.forms.get('ACTION') == 'DELETE':
            # Get job properties from DB
            job = Job(jobname, jobid, user)
            # Delete job
            job.delete()
            logger.info('{} {} DELETED'.format(jobname, jobid))
        else:
            raise UserWarning('ACTION=DELETE is not specified in POST')
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except CalledProcessError as e:
        abort_500_except(msg='STDERR output:\n' + e.output, msg_public='Cannot connect to the computing cluster')
    except:
        abort_500_except()
    redirect(BASE_URL + '/rest/' + jobname, 303)


# ----------
# /<jobname>/<jobid>/phase
# ----------


@app.route('/rest/<jobname>/<jobid>/phase')
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
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.phase
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.post('/rest/<jobname>/<jobid>/phase')
def post_phase(jobname, jobid):
    """Change Phase of job <jobid> --> start or abort job

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        if 'PHASE' in request.forms:
            new_phase = request.forms.get('PHASE')
            logger.info('PHASE={} {} {}'.format(new_phase, jobname, jobid))
            if new_phase == 'RUN':
                # Get job properties from DB
                job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True)
                # Check if phase is PENDING
                if job.phase not in ['PENDING']:
                    raise UserWarning('Job has to be in PENDING phase')
                # Start job
                job.start()
                logger.info('{} {} STARTED with process_id={}'
                            ''.format(jobname, jobid, str(job.process_id)))
            elif new_phase == 'ABORT':
                # Get job properties from DB
                job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True, get_results=True)
                # Abort job
                job.abort()
                logger.info('{} {} ABORTED'.format(jobname, jobid))
            else:
                raise UserWarning('PHASE=' + new_phase + ' not expected')
        else:
            raise UserWarning('PHASE keyword is not specified in POST')
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except CalledProcessError as e:
        abort_500_except(msg='STDERR output:\n' + e.output, msg_public='Cannot connect to the computing cluster')
    except:
        abort_500_except()
    # Response
    redirect(BASE_URL + '/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>/executionduration
# ----------


@app.route('/rest/<jobname>/<jobid>/executionduration')
def get_executionduration(jobname, jobid):
    """Get the maximum execution duration of job <jobid>

    Returns:
        200 OK: text/plain: integer number of seconds (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.execution_duration)
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.post('/rest/<jobname>/<jobid>/executionduration')
def post_executionduration(jobname, jobid):
    """Change the maximum execution duration of job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get value from POST
        if 'EXECUTIONDURATION' not in request.forms:
            raise UserWarning('EXECUTIONDURATION keyword required')
        new_value = request.forms.get('EXECUTIONDURATION')
        # Check new value
        try:
            new_value = int(new_value)
        except ValueError:
            raise UserWarning('Execution duration must be an integer or a float')
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        if job.phase == 'PENDING':
            # Change value
            job.set_attribute('execution_duration', new_value)
            logger.info('{} {} set execution_duration={}'.format(jobname, jobid, str(new_value)))
        else:
            raise UserWarning('Job "{}" must be in PENDING state (currently {}) to change execution duration'
                              ''.format(jobid, job.phase))
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except:
        abort_500_except()
    # Response
    redirect(BASE_URL + '/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>/destruction
# ----------


@app.route('/rest/<jobname>/<jobid>/destruction')
def get_destruction(jobname, jobid):
    """Get the destruction instant for job <jobid>

    Returns:
        200 OK: text/plain: time in ISO8601 format (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.destruction_time
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.post('/rest/<jobname>/<jobid>/destruction')
def post_destruction(jobname, jobid):
    """Change the destruction instant for job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid> (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get value from POST
        if 'DESTRUCTION' not in request.forms:
            raise UserWarning('DESTRUCTION keyword required')
        new_value = request.forms.get('DESTRUCTION')
        # Check if ISO8601 format, truncate if unconverted data remains
        try:
            dt.datetime.strptime(new_value, DT_FMT)
        except ValueError as e:
            if len(e.args) > 0 and e.args[0].startswith('unconverted data remains:'):
                new_value = new_value[:19]
            else:
                raise UserWarning('Destruction time must be in ISO8601 format ({})'.format(str(e)))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Change value
        # job.set_destruction_time(new_value)
        job.set_attribute('destruction_time', new_value)
        logger.info('{} {} set destruction_time={}'.format(jobname, jobid, new_value))
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except:
        abort_500_except()
    # Response
    redirect(BASE_URL + '/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>/error
# ----------


@app.route('/rest/<jobname>/<jobid>/error')
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
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.error
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/quote
# ----------


@app.route('/rest/<jobname>/<jobid>/quote')
def get_quote(jobname, jobid):
    """Get the Quote for job <jobid>

    Returns:
        200 OK: text/plain: integer number of seconds (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.quote)
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/parameters
# ----------


@app.route('/rest/<jobname>/<jobid>/parameters')
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
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        # Return job parameters in UWS format
        xml_out = job.parameters_to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.route('/rest/<jobname>/<jobid>/parameters/<pname>')
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
        logger.info('param=' + pname + ' ' + jobname + ' ' + jobid)
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        # Check if param exists
        if pname not in job.parameters:
            raise storage.NotFoundWarning('Parameter "{}" NOT FOUND for job "{}"'.format(pname, jobid))
        # Return parameter
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.parameters[pname]['value'])
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.post('/rest/<jobname>/<jobid>/parameters/<pname>')
def post_parameter(jobname, jobid, pname):
    """Change the parameter value for job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid>/parameters (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('pname={} {} {}'.format(pname, jobname, jobid))
        # Get value from POST
        if 'VALUE' not in request.forms:
            raise UserWarning('VALUE keyword required')
        new_value = request.forms.get('VALUE')
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        # TODO: Check if new_value format is correct (from JDL?)
        # Change value
        if job.phase == 'PENDING':
            job.set_parameter(pname, new_value)
            logger.info('{} {} set parameter {}={}'.format(jobname, jobid, pname, new_value))
        else:
            raise UserWarning('Job "{}" must be in PENDING state (currently {}) to change parameter'
                              ''.format(jobid, job.phase))
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except UserWarning as e:
        abort_500(e.args[0])
    except:
        abort_500_except()
    # Response
    redirect(BASE_URL + '/rest/' + jobname + '/' + jobid + '/parameters', 303)


# ----------
# /<jobname>/<jobid>/results
# ----------


@app.route('/rest/<jobname>/<jobid>/results')
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
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_results=True)
        # Return job results in UWS format
        xml_out = job.results_to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.route('/rest/<jobname>/<jobid>/results/<rname>')
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
        logger.info('rname={} {} {}'.format(rname, jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_results=True)
        # Check if result exists
        if rname not in job.results:
            raise storage.NotFoundWarning('Result "{}" NOT FOUND for job "{}"'.format(rname, jobid))
        # Return result
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.results[rname]['url'])
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.route('/rest/<jobname>/<jobid>/stdout')
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
        logname = 'stdout'
        logroot = '{}/{}'.format(JOBDATA_PATH, jobid)
        if not os.path.isfile(os.path.join(logroot, logname + '.log')):
            # TODO: get from manager if not available, only available when EXECUTING
            raise storage.NotFoundWarning('Log "{}" NOT FOUND for job "{}"'.format(logname, jobid))
        # Return file
        return static_file(logname + '.log', root=logroot, mimetype='text')
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.route('/rest/<jobname>/<jobid>/stderr')
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
        logname = 'stderr'
        logroot = '{}/{}'.format(JOBDATA_PATH, jobid)
        if not os.path.isfile(os.path.join(logroot, logname + '.log')):
            # TODO: get from manager if not available, only available when EXECUTING
            raise storage.NotFoundWarning('Log "{}" NOT FOUND for job "{}"'.format(logname, jobid))
        # Return file
        return static_file(logname + '.log', root=logroot, mimetype='text')
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


@app.route('/rest/<jobname>/<jobid>/prov<provtype>')
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
        provname = 'provenance.' + provtype
        provroot = '{}/{}'.format(JOBDATA_PATH, jobid)
        if not os.path.isfile(os.path.join(provroot, provname)):
            raise storage.NotFoundWarning('Prov file "{}" NOT FOUND for job "{}"'.format(provname, jobid))
        # Return file
        content_types = {
            'json': 'application/json',
            'xml': 'text/xml',
            'svg': 'image/svg+xml',
        }
        return static_file(provname, root=provroot, mimetype=content_types[provtype])
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/owner
# ----------


@app.route('/rest/<jobname>/<jobid>/owner')
def get_owner(jobname, jobid):
    """Get the owner of the job <jobid>

    Returns:
        200 OK: text/plain: an appropriate identifier as discussed in 3 (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    try:
        logger.info('{} {}'.format(jobname, jobid))
        # Get job properties from DB
        job = Job(jobname, jobid, user)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.owner
    except JobAccessDenied as e:
        abort_403(str(e))
    except storage.NotFoundWarning as e:
        abort_404(str(e))
    except:
        abort_500_except()


# ----------
# run server
# ----------


if __name__ == '__main__':
    # Run local web server
    run(app, host='localhost', port=8082, debug=False, reloader=True)
