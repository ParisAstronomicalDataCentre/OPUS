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
from flask import Flask, request, abort, redirect, url_for, session, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from flask_login import user_logged_in, user_logged_out, current_user
#from bottle import Bottle, request, response, abort, redirect, run, static_file, parse_auth, TEMPLATE_PATH, view, jinja2_view
#from beaker.middleware import SessionMiddleware
#from cork import Cork
#from wsgiproxy.app import WSGIProxyApp
from wsgiproxy import HostProxy
try:
    import urlparse
except ImportError:  # pragma: nocover
    import urllib.parse as urlparse  # NOQA


APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
APPLICATION_ROOT = '/client'
#UWS_SERVER_URL = 'http://localhost:8080'
UWS_SERVER_URL = 'http://localhost'
#UWS_SERVER_URL = 'http://localhost/proxy'
#UWS_SERVER_URL = 'https://voparis-uws-test.obspm.fr'
ALLOW_ANONYMOUS = False

#--- Include host-specific settings ------------------------------------------------------------------------------------
if os.path.exists(APP_PATH + '/uws_client/settings_local.py'):
    from settings_local import *
#--- Include host-specific settings ------------------------------------------------------------------------------------


# Set logger
LOG_PATH = '/var/www/opus/logs'
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
    }
}

# Set path to uws_client templates
#TEMPLATE_PATH.insert(0, APP_PATH + '/uws_client/templates/')

# Set logger
logging.config.dictConfig(LOGGING)
logger = logging.getLogger('uws_client')
logger.info('Load flask client')

app = Flask(__name__) # create the application instance :)
app.secret_key = b'\ttrLu\xdd\xde\x9f\xd2}\xc1\x0e\xb6\xe6}\x95\xc6\xb1\x8f\xa09\xf5\x1aG'

app.config.from_object(__name__) # load config from this file , flaskr.py

# Load default config and override config from an environment variable
app.config.update(dict(
    APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)),
    APPLICATION_ROOT = '/client',
    #UWS_SERVER_URL = 'http://localhost:8080',
    UWS_SERVER_URL = 'http://localhost',
    #UWS_SERVER_URL = 'http://localhost/proxy',
    #UWS_SERVER_URL = 'https://voparis-uws-test.obspm.fr',
    ALLOW_ANONYMOUS = False,
    DEBUG = True,
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
))

# ----------
#  User DB

db = SQLAlchemy(app)

# Define models
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
    password = db.Column(db.String(255))
    pid = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

@app.before_first_request
def load_in_session():
    session['server_url'] = app.config['UWS_SERVER_URL']

# Create a user to test with
@app.before_first_request
def create_admin_user():
    try:
        db.create_all()
        user_datastore.create_role(name='user')
        user_datastore.create_role(name='admin')
        pid = uuid.uuid5(uuid.NAMESPACE_X500, APP_PATH + 'admin')
        user_datastore.create_user(
            email='admin',
            password='cta',
            pid=str(pid),
            active=True,
            roles=['admin'],
        )
        db.session.commit()
    except:
        db.session.rollback()
        logger.warning('Database already exists')

# ----------
# Manage user accounts


# @app.route('/accounts/login', methods=['GET', 'POST'])
# @anonymous_user_required
# def login_user():
#     # Login user
#     if request.method == 'POST':
#
#         session['username'] = request.form['username']
#         flash('You were logged in', 'alert-info')
#         return redirect(url_for('home'))
#     # Serve login form
#     next_page = request.args.get('next', APPLICATION_ROOT)
#     context = dict(
#         next=next_page,
#     )
#     return render_template('login_form.html', **context)


# @app.route('/accounts/logout')
# def logout():
#     session.pop('username', None)
#     flash('You were logged out', 'alert-info')
#     return redirect(url_for('home'))


@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    flash('You were logged in', 'info')
    session['auth'] = base64.b64encode(current_user.email + ':' + str(current_user.pid))


@user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    flash('You were logged out', 'info')


@app.route('/accounts/profile')
@login_required
def profile():
    return render_template('profile.html')


# ----------
# Web Pages


@app.route('/')
def home():
    """Home page"""
    logger.info(session)
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
@app.route('/job_definition/<path:jobname>', methods=['GET', 'POST'])
def job_definition(jobname):
    """Show form for new job definition"""
    logger.info(jobname)
    # No need to authenticate, users can propose new jobs that will be validated
    if request.method == 'POST':
        jobname = request.form.get('name').split('/')[-1]
        logger.info('Create new/{}'.format(jobname))
        r = requests.post('{}/config/job_definition'.format(app.config['UWS_SERVER_URL']), data=request.form)
        if r.status_code == 200:
            flash('New job definition has been saved as new/{}'.format(jobname), 'info')
        else:
            flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
        return redirect(url_for('job_definition', jobname='/new/{}'.format(jobname)), 303)
    # Show form
    # Set is_admin (will show validate button)
    is_admin = False
    if current_user.is_authenticated:
        if 'admin' in current_user.roles:
            is_admin = True
    msg = request.args.get('msg', '')
    msg_text = {
        'restricted': 'Access is restricted to administrators',
        'new': 'New job definition has been saved as {}'.format(jobname),
        'validated': 'Job definition for new/{jn} has been validated and renamed {jn}'.format(jn=jobname),
        'script_copied': 'Job script {}.sh has been copied to work cluster'.format(jobname),
        'notfound': 'Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname),
    }
    return render_template('job_definition.html', jobname=jobname, is_admin=is_admin)


@app.route('/validate_job/<jobname>')
@login_required
def validate_job(jobname):
    """
    Validate job on server
    :param jobname:
    :return:
    """
    logger.info(jobname)
    # Authenticate user
    #next_url = str(request.urlparts.path)
    #aaa.require(fail_redirect=ENDPOINT + '/accounts/login?next=' + next_url)
    # Send request to UWS Server
    r = requests.get('{}/config/validate_job/{}'.format(UWS_SERVER_URL, jobname))
    # redirect to job_definition with message
    if r.status_code == 200:
        flash('Job definition for new/{jn} has been validated and renamed {jn}'.format(jn=jobname))
    else:
        flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
    return redirect(url_for('job_definition', jobname=jobname), 303)


@app.route('/cp_script/<jobname>')
def cp_script(jobname):
    """
    Validate job on server
    :param jobname:
    :return:
    """
    logger.info(jobname)
    # Authenticate user
    #next_url = str(request.urlparts.path)
    #aaa.require(fail_redirect=ENDPOINT + '/accounts/login?next=' + next_url)
    # Send request to UWS Server
    r = requests.get('{}/config/cp_script/{}'.format(UWS_SERVER_URL, jobname))
    # redirect to job_definition with message
    if r.status_code == 200:
        flash('Job script {}.sh has been copied to work cluster'.format(jobname))
    else:
        flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
    return redirect(url_for('job_definition', jobname=jobname), 303)


# ----------
# Proxy (to avoid cross domain calls)


class MyProxy(HostProxy):
    def process_request(self, uri, method, headers, environ):
        uri = uri.replace('/proxy', '')
        logger.info(environ)
        logger.info(method + ' ' + uri)
        return self.http(uri, method, environ['wsgi.input'], headers)

proxy_app = MyProxy('https://voparis-uws-test.obspm.fr/', strip_script_name=False, client='requests')
#app.mount(ENDPOINT + '/proxy', proxy_app)
#app.register_blueprint(proxy_app, url_prefix='/proxy')

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
