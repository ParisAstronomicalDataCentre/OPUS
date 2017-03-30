#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
UWS client implementation using bottle.py and javascript
"""

import os
import uuid
import base64
import requests
import logging
from bottle import Bottle, request, response, abort, redirect, run, static_file, parse_auth, TEMPLATE_PATH, view, jinja2_view
from beaker.middleware import SessionMiddleware
from cork import Cork


# ----------
#  Settings


APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
ENDPOINT = 'client'
UWS_SERVER_URL = 'http://localhost:8080'
ALLOW_ANONYMOUS = False

#--- Include host-specific settings ------------------------------------------------------------------------------------
if os.path.exists('uws_client/settings_local.py'):
    from uws_client.settings_local import *
#--- Include host-specific settings ------------------------------------------------------------------------------------

# Set logger
LOG_PATH = APP_PATH + '/logs'
LOG_FILE_SUFFIX = ''
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s %(funcName)s: %(message)s'
        },
    },
    'handlers': {
        'file_client': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/client' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'default'
        },
    },
    'loggers': {
        'uws_client': {
            'handlers': ['file_client'],
            'level': 'DEBUG',
        },
    }
}

# Set logger
if ('uws_client' not in logging.Logger.manager.loggerDict):
    logging.config.dictConfig(LOGGING)
logger = logging.getLogger('uws_client')

# Set path to uws_client templates
TEMPLATE_PATH.insert(0, APP_PATH + '/uws_client/views/')


# ----------
# Create application


app = Bottle()

# Session option (create session after code)
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': 'please use a random key and keep it secret!',
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}

# Start authentication system
aaa = Cork(APP_PATH + '/uws_client/cork_conf')


# ----------
# Helper functions


@app.route('/static/<path:path>')
def static(path):
    """Access to static files (css, js, ...)"""
    return static_file(path, root='{}/uws_client/static'.format(APP_PATH))


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root=APP_PATH)


# ----------
# Manage user accounts


@app.route('/accounts/login')
@jinja2_view('login_form.html')
def login_form():
    """Serve login form"""
    session = request.environ['beaker.session']
    next_page = request.query.get('next', '/')
    msg = request.query.get('msg', '')
    msg_text = {
        'failed': 'Authentication failed',
    }
    if msg in msg_text:
        return {'session': session, 'next': next_page, 'message': msg_text[msg]}
    return {'session': session, 'next': next_page}


@app.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'


def postd():
    return request.forms


def post_get(name, default=''):
    return request.POST.get(name, default).strip()


@app.post('/accounts/login')
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    next_page = post_get('next')
    # Create Basic Auth for requests to UWS Server, Save to session
    session = request.environ['beaker.session']
    # PID is a UUID based on APP_PATH and username, so specific to user and client app
    pid = uuid.uuid5(uuid.NAMESPACE_X500, APP_PATH + username)
    session['auth'] = base64.b64encode(username + ':' + str(pid))
    session.save()
    # Login
    logger.info(username)
    aaa.login(username, password, success_redirect=next_page, fail_redirect='/accounts/login?msg=failed')

@app.route('/accounts/logout')
def logout():
    #session = request.environ['beaker.session']
    #logger.info(session.username)
    aaa.logout(success_redirect='/')


@app.route('/accounts/admin')
@view('admin_page')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/?msg=restricted')
    return dict(
        current_user=aaa.current_user,
        users=aaa.list_users(),
        roles=aaa.list_roles()
    )


@app.post('/accounts/create_user')
def create_user():
    try:
        aaa.create_user(postd().username, postd().role, postd().password)
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@app.post('/accounts/delete_user')
def delete_user():
    try:
        aaa.delete_user(post_get('username'))
        return dict(ok=True, msg='')
    except Exception, e:
        print repr(e)
        return dict(ok=False, msg=e.message)


@app.post('/accounts/create_role')
def create_role():
    try:
        aaa.create_role(post_get('role'), post_get('level'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@app.post('/accounts/delete_role')
def delete_role():
    try:
        aaa.delete_role(post_get('role'))
        return dict(ok=True, msg='')
    except Exception, e:
        return dict(ok=False, msg=e.message)


@app.route('/accounts/change_password')
@view('password_change_form')
def change_password():
    """Show password change form"""
    aaa.require(role='admin', fail_redirect='/?msg=restricted')
    return dict()


@app.post('/accounts/change_password')
def change_password():
    """Change password"""
    #aaa.reset_password(post_get('reset_code'), post_get('password'))
    user = aaa.user(post_get('username'))
    if post_get('password'):
        user.update(pwd=post_get('password'))
    if post_get('role'):
        user.update(role=post_get('role'))
    if post_get('email'):
        user.update(email_addr=post_get('email'))
    return 'Thanks. <a href="/accounts/admin">Go to admin page</a>'


# ----------
# Web Pages


@app.route('/')
@jinja2_view('home.html')
def home():
    """Home page"""
    session = request.environ['beaker.session']
    session['server_url'] = UWS_SERVER_URL
    session.save()
    msg = request.query.get('msg', '')
    msg_text = {
        'restricted': 'Access is restricted to administrators',
    }
    if msg in msg_text:
        return {'session': session, 'message': msg_text[msg]}
    return {'session': session}
    # response.content_type = 'text/html; charset=UTF-8'
    # return "UWS v1.0 server implementation<br>(c) Observatoire de Paris 2015"


@app.route('/client/job_list')
@jinja2_view('job_list.html')
def job_list():
    """Job list page"""
    logger.info('')
    if not ALLOW_ANONYMOUS:
        aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    session = request.environ['beaker.session']
    session['server_url'] = UWS_SERVER_URL
    session.save()
    jobname = request.query.get('jobname', '')
    return {'session': session, 'jobname': jobname}


@app.route('/client/job_edit/<jobname>/<jobid>')
@jinja2_view('job_edit.html')
def job_edit(jobname, jobid):
    """Job edit page"""
    logger.info(jobname + ' ' + jobid)
    if not ALLOW_ANONYMOUS:
        aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    session = request.environ['beaker.session']
    session['server_url'] = UWS_SERVER_URL
    session.save()
    return {'session': session, 'jobname': jobname, 'jobid': jobid}


@app.route('/client/job_form/<jobname>')
@jinja2_view('job_form.html')
def job_form(jobname):
    """Job edit page"""
    logger.info(jobname)
    if not ALLOW_ANONYMOUS:
        aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    session = request.environ['beaker.session']
    session['server_url'] = UWS_SERVER_URL
    session.save()
    return {'session': session, 'jobname': jobname}


@app.get('/client/job_definition')
@jinja2_view('job_definition.html')
def job_definition():
    """Show form for new job definition"""
    logger.info('')
    # No need to authenticate, users can propose new jobs that will be validated
    # aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    # Set is_admin (will show validate button)
    is_admin = False
    if not aaa.user_is_anonymous:
        if aaa.current_user.role == 'admin':
            is_admin = True
    session = request.environ['beaker.session']
    session['server_url'] = UWS_SERVER_URL
    session.save()
    jobname = request.query.get('jobname', '')
    msg = request.query.get('msg', '')
    msg_text = {
        'restricted': 'Access is restricted to administrators',
        'new': 'New job definition has been saved as {}'.format(jobname),
        'validated': 'Job definition for new/{jn} has been validated and renamed {jn}'.format(jn=jobname),
        'script_copied': 'Job script {}.sh has been copied to work cluster'.format(jobname),
        'notfound': 'Job definition for new/{jn} was not found on the server. Cannot validate.'.format(jn=jobname),
    }
    if msg in msg_text:
        return {'session': session, 'is_admin': is_admin, 'jobname': jobname, 'message': msg_text[msg]}
    return {'session': session, 'is_admin': is_admin, 'jobname': jobname}


@app.post('/client/job_definition')
def client_create_new_job_definition():
    """
    Use filled form to create a JDL file on server for the given job
    :return:
    """
    jobname = request.forms.get('name').split('/')[-1]
    logger.info(jobname)
    # Authenticate user
    next_url = str(request.urlparts.path)
    aaa.require(fail_redirect='/accounts/login?next=' + next_url)
    # Send POST request to server
    data = request.POST.dict
    r = requests.post('{}/config/job_definition'.format(UWS_SERVER_URL), data=data)
    # Redirect to job_definition with message
    if r.status_code == 200:
        msg = 'new'
    else:
        msg = 'notfound'
    redirect('/client/job_definition?jobname=new/{}&msg={}'.format(jobname, msg), 303)


@app.get('/client/validate_job/<jobname>')
def client_validate_job(jobname):
    """
    Validate job on server
    :param jobname:
    :return:
    """
    logger.info(jobname)
    # Authenticate user
    next_url = str(request.urlparts.path)
    aaa.require(fail_redirect='/accounts/login?next=' + next_url)
    # Send request to UWS Server
    r = requests.get('{}/config/validate_job/{}'.format(UWS_SERVER_URL, jobname))
    # redirect to job_definition with message
    if r.status_code == 200:
        msg = 'validated'
    else:
        msg = 'notfound'
    redirect('/client/job_definition?jobname={}&msg={}'.format(jobname, msg), 303)


@app.get('/client/cp_script/<jobname>')
def client_cp_script(jobname):
    """
    Validate job on server
    :param jobname:
    :return:
    """
    logger.info(jobname)
    # Authenticate user
    next_url = str(request.urlparts.path)
    aaa.require(fail_redirect='/accounts/login?next=' + next_url)
    # Send request to UWS Server
    r = requests.get('{}/config/cp_script/{}'.format(UWS_SERVER_URL, jobname))
    # redirect to job_definition with message
    if r.status_code == 200:
        msg = 'script_copied'
    else:
        msg = 'notfound'
    redirect('/client/job_definition?jobname={}&msg={}'.format(jobname, msg), 303)


# ----------
# run server


# Create session
client_app = SessionMiddleware(app, session_opts)

if __name__ == '__main__':
    # Run local web server
    run(client_app, host='localhost', port=8080, debug=False, reloader=True)
