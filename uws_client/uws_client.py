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
from requests.auth import HTTPBasicAuth
import logging
import logging.config
from flask import Flask, request, abort, redirect, url_for, session, g, render_template, flash, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, roles_required
from flask_login import user_logged_in, user_logged_out, current_user
# from werkzeug.wsgi import DispatcherMiddleware
# from wsgiproxy import HostProxy

# Configuration

#DEBUG=False
#TESTING=False
#SERVER_NAME=  # (e.g.: 'myapp.dev:5000')
APPLICATION_ROOT = '/client'
ENDPOINT = '/client'
# UWS_SERVER_URL = 'http://localhost'
UWS_SERVER_URL = 'https://voparis-uws-test.obspm.fr'
UWS_SERVER_URL_JS = '/client/proxy'  # called by javascript, set to local url to avoid cross-calls
UWS_AUTH = 'Basic'
ALLOW_ANONYMOUS = False
# CHUNK_SIZE = 1024
LOG_PATH = '/var/www/opus/logs'
LOG_FILE_SUFFIX = ''

SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/opus/db/flask_login.db',
SQLALCHEMY_TRACK_MODIFICATIONS = False,
SECURITY_PASSWORD_SALT = 'test',
SECURITY_URL_PREFIX = '/accounts',
SECURITY_FLASH_MESSAGES = True,
SECURITY_POST_LOGIN_VIEW = '/client',
SECURITY_POST_LOGOUT_VIEW = '/client',
SECURITY_USER_IDENTITY_ATTRIBUTES = ['email'],
#SECURITY_REGISTERABLE = True,
#SECURITY_CHANGEABLE = True,

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

#--- Include host-specific settings ------------------------------------------------------------------------------------
if os.path.exists(APP_PATH + '/uws_client/settings_local.py'):
    from settings_local import *
#--- Include host-specific settings ------------------------------------------------------------------------------------

# Set logger
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s %(funcName)s: %(message)s'
        },
    },
    'handlers': {
        'file_client_flask': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_PATH + '/client_flask' + LOG_FILE_SUFFIX + '.log',
            'formatter': 'default'
        },
    },
    'loggers': {
        'uws_client': {
            'handlers': ['file_client_flask'],
            'level': 'DEBUG',
        },
        'wsgiproxy': {
            'handlers': ['file_client_flask'],
            'level': 'DEBUG',
        },
    }
}

# Set path to uws_client templates
#TEMPLATE_PATH.insert(0, app.config['APP_PATH'] + '/uws_client/templates/')

# Set logger
logging.config.dictConfig(LOGGING)
logger = logging.getLogger('uws_client')
logger.info('Load flask client')

app = Flask(__name__) # create the application instance :)
app.secret_key = b'\ttrLu\xdd\xde\x9f\xd2}\xc1\x0e\xb6\xe6}\x95\xc6\xb1\x8f\xa09\xf5\x1aG'

app.config.from_object(__name__) # load config from this file

# Load default config and override config from an environment variable
#app.config.update(dict())

# ----------
#  User DB

db = SQLAlchemy(app)

# Define models for User and Role
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    # username = db.Column(String(255))
    password = db.Column(db.String(255))
    pid = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# @app.before_first_request
# def load_in_session():
#     logger.warning('Set server_url in session')
#     session['server_url'] = app.config['UWS_SERVER_URL_JS']


# Create a user to test with
@app.before_first_request
def create_db():
    try:
        db.create_all()
        user_datastore.create_role(name='user')
        user_datastore.create_role(name='admin')
        # Create admin user
        pid = uuid.uuid5(uuid.NAMESPACE_X500, app.config['APP_PATH'] + 'admin')
        user_datastore.create_user(
            email='admin',
            password='cta',
            pid=str(pid),
            active=True,
            roles=['admin'],
        )
        # Create demo user
        pid = uuid.uuid5(uuid.NAMESPACE_X500, app.config['APP_PATH'] + 'user')
        user_datastore.create_user(
            email='user',
            password='cta',
            pid=str(pid),
            active=True,
            roles=['user'],
        )
        db.session.commit()
        logger.warning('Database created')
    except Exception as e:
        db.session.rollback()
        logger.warning(e.message)


# ----------
# Manage user accounts using flask_security (flask_login)


@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    logger.info(user.email)
    session['server_url'] = app.config['UWS_SERVER_URL_JS']
    session['auth'] = base64.b64encode(current_user.email + ':' + str(current_user.pid))
    flash('"{}" is now logged in'.format(user.email), 'info')


@user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    logger.info(user.email)
    flash('"{}" is now logged out'.format(user.email), 'info')


@app.route('/accounts/profile')
@login_required
def profile():
    return render_template('profile.html')


# ----------
# Web Pages


@app.route('/')
def home():
    """Home page"""
    logger.info(session.__dict__)
    return render_template('home.html')


@app.route('/job_list/', defaults={'jobname': ''})
@app.route('/job_list/<jobname>')
@login_required
def job_list(jobname):
    """Job list page"""
    logger.info(jobname)
    return render_template('job_list.html', jobname=jobname)


@app.route('/job_edit/<jobname>/<jobid>')
@login_required
def job_edit(jobname, jobid):
    """Job edit page"""
    logger.info(jobname + ' ' + jobid)
    return render_template('job_edit.html', jobname=jobname, jobid=jobid)


@app.route('/job_form/<jobname>')
@login_required
def job_form(jobname):
    """Job edit page"""
    logger.info(jobname)
    return render_template('job_form.html', jobname=jobname)


@app.route('/job_definition', methods=['GET', 'POST'], defaults={'jobname': ''})
@app.route('/job_definition/<path:jobname>', methods=['GET'])
def job_definition(jobname):
    """Show form for new job definition"""
    logger.info(jobname)
    # No need to authenticate, users can propose new jobs that will be validated
    if request.method == 'POST':
        jobname = request.form.get('name').split('/')[-1]
        logger.info('Create new/{}'.format(jobname))
        r = uws_server_request('/config/job_definition'.format(jobname), method='POST', data=request.form, headers=request.headers)
        if r.status_code == 200:
            flash('New job definition has been saved as new/{}'.format(jobname), 'info')
        else:
            flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
        return redirect(url_for('job_definition', jobname='/new/{}'.format(jobname)), 303)
    # Show form
    # Set is_admin (will show validate buttons)
    is_admin = False
    if current_user.is_authenticated and current_user.has_role('admin'):
        is_admin = True
    return render_template('job_definition.html', jobname=jobname, is_admin=is_admin)


@app.route('/validate_job/<jobname>')
@login_required
@roles_required('admin')
def validate_job(jobname):
    """Validate job on server"""
    logger.info(jobname)
    # Send request to UWS Server
    r = uws_server_request('/config/validate_job/{}'.format(jobname), method='GET', headers=request.headers)
    # redirect to job_definition with message
    if r.status_code == 200:
        flash('Job definition for new/{jn} has been validated and renamed {jn}'.format(jn=jobname))
    else:
        flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
    return redirect(url_for('job_definition', jobname=jobname), 303)


@app.route('/cp_script/<jobname>')
@login_required
@roles_required('admin')
def cp_script(jobname):
    """Copy job script to work server"""
    logger.info(jobname)
    # Send request to UWS Server
    r = uws_server_request('/config/cp_script/{}'.format(jobname), method='GET')
    # redirect to job_definition with message
    if r.status_code == 200:
        flash('Job script {}.sh has been copied to work cluster'.format(jobname))
    else:
        flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
    return redirect(url_for('job_definition', jobname=jobname), 303)


# ----------
# Proxy (to avoid cross domain calls and add Auth header)


@app.route('/proxy/<path:uri>', methods=['GET', 'POST'])
def proxy(uri):
    r = uws_server_request('/' + uri, method=request.method, params=request.args, data=request.form, headers=request.headers)
    # logger.debug(r.headers.__dict__)
    # def generate():
    #     for chunk in r.iter_content(CHUNK_SIZE):
    #         yield chunk
    # return Response(stream_with_context(generate()), content_type = r.headers['content-type'])
    # headers = {}
    # for k in ['content-length']:  #, 'content-encoding']:
    #     headers[k] = r.headers[k]
    return Response(r, status=r.status_code, content_type=r.headers['content-type'])  # , headers=headers)


def uws_server_request(uri, method='GET', params=None, data=None, headers={}):
    # logger.debug(headers.__dict__)
    # Add auth information (Basic, Token...)
    auth = None
    if UWS_AUTH == 'Basic':
        auth = HTTPBasicAuth(current_user.email, current_user.pid)
    # Send request
    if method == 'POST':
        r = requests.post('{}{}'.format(UWS_SERVER_URL, uri), data=data, auth=auth)
    else:
        r = requests.get('{}{}'.format(UWS_SERVER_URL, uri), params=params, auth=auth)
    # Return response
    logger.info("{} {} ({})".format(request.method, uri, r.status_code))
    return r


# class MyProxy(HostProxy):
#     def process_request(self, uri, method, headers, environ):
#         uri = uri.replace(app.config['APPLICATION_ROOT'] + '/proxy', '')
#         #headers['Authorization'] = app.
#         logger.debug(headers)
#         logger.debug(method + ' ' + uri)
#         return self.http(uri, method, environ['wsgi.input'], headers)
#
# proxy_app = MyProxy('https://voparis-uws-test.obspm.fr/', strip_script_name=False)
#
# app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/proxy': proxy_app})

# TODO: Need to set 'HTTP_AUTHORIZATION': 'Basic YWRtaW46NzQyY2M5N2ItMjgwYi01MTZhLWJkNDUtYjY4NGM3ZmZiNDY1' from proxy, not from javascript


# ----------
# run server


# Create session
#client_app = SessionMiddleware(app, session_opts)
client_app = app

if __name__ == '__main__':
    # Run local web server
    #run(client_app, host='localhost', port=8080, debug=False, reloader=True)
    pass
