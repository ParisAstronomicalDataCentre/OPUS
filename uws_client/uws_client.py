#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
UWS client implementation using bottle.py and javascript
"""

import os
import yaml
import uuid
import datetime
import base64
import requests
from requests.auth import HTTPBasicAuth
import logging
import logging.config
from flask import Flask, request, abort, redirect, url_for, session, g, current_app, render_template, flash, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, roles_required, utils
from flask_security.forms import LoginForm, RegisterForm
from flask_login import user_logged_in, user_logged_out, current_user
from flask_admin import Admin
from flask_admin.contrib import sqla
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired


# Configuration

# App configuration
#DEBUG=False
#TESTING=False
#SERVER_NAME=  # (e.g.: 'myapp.dev:5000')
APPLICATION_ROOT = '/client'
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
VAR_PATH = '/var/www/opus'
LOG_FILE_SUFFIX = ''
UWS_SERVER_URL_JS = '/client/proxy'  # called by javascript, set to local url to avoid cross-calls

# Default editable configuration
EDITABLE_CONFIG = dict(
    # UWS_SERVER_URL = 'http://localhost',
    UWS_SERVER_URL = 'https://voparis-uws-test.obspm.fr',
    UWS_AUTH = 'Basic',
    ALLOW_ANONYMOUS = False,
)

#--- Include host-specific settings ------------------------------------------------------------------------------------
if os.path.exists(APP_PATH + '/uws_client/settings_local.py'):
    from settings_local import *
#--- Include host-specific settings ------------------------------------------------------------------------------------

LOG_PATH = VAR_PATH + '/logs'  # the logs dir has to be writable from the app
CONFIG_FILE = VAR_PATH + '/config/uws_client_config.yaml'  # the config dir has to be writable from the app
SQLALCHEMY_DATABASE_URI = 'sqlite:///{}/db/flask_login.db'.format(VAR_PATH)  # SQLALCHEMY_DATABASE_URI_LOCAL,
SQLALCHEMY_TRACK_MODIFICATIONS = True
SECURITY_PASSWORD_SALT = 'test'
SECURITY_URL_PREFIX = '/accounts'
SECURITY_FLASH_MESSAGES = True
SECURITY_POST_LOGIN_VIEW = APPLICATION_ROOT
SECURITY_POST_LOGOUT_VIEW = APPLICATION_ROOT
SECURITY_USER_IDENTITY_ATTRIBUTES = 'email'
SECURITY_REGISTERABLE = False
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGEABLE = True
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False

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
logger.debug('Load flask client')


# ----------
# create the application instance :)


app = Flask(__name__, instance_relative_config=True, instance_path=VAR_PATH)
app.secret_key = b'\ttrLu\xdd\xde\x9f\xd2}\xc1\x0e\xb6\xe6}\x95\xc6\xb1\x8f\xa09\xf5\x1aG'
app.config.update(EDITABLE_CONFIG)  # Default editable config
app.config.from_object(__name__)  # load config from this file


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
    def __repr__(self):
        return self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    # username = db.Column(db.String(255), unique=True, index=True)
    password = db.Column(db.String(255))
    pid = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime(), default=datetime.datetime.now)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    def __repr__(self):
        return self.email


class ExtendedLoginForm(LoginForm):
    email = StringField('Username or Email Address', [InputRequired()])


class ExtendedRegisterForm(RegisterForm):
    email = StringField('Username or Email Address', [InputRequired()])


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore , login_form=ExtendedLoginForm)
#, register_form=ExtendedRegisterForm)

# ----------
# Load/store g.config (different from app.config, g.config can be set by the admin user through the Preferences page)

@app.before_first_request
def load_config():
    logger.debug('Load editable config')
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as cf:
            econf = yaml.load(cf)
            app.config.update(econf)
    else:
        save_config()

def save_config():
    logger.debug('Save editable config')
    with open(CONFIG_FILE, 'w') as cf:
        econf = {k: app.config[k] for k in EDITABLE_CONFIG.keys() if k in app.config}
        yaml.dump(econf, cf, default_flow_style=False)

def update_config(key, value):
    if key in EDITABLE_CONFIG:
        app.config[key] = value
        save_config()


# ----------
# Create default database


@app.before_first_request
def create_db():
    try:
        db.create_all()
        user_datastore.find_or_create_role(
            name='user',
            description='User',
        )
        user_datastore.find_or_create_role(
            name='admin',
            description='Administrator',
        )
        # Create admin user
        if not user_datastore.get_user('admin'):
            pid = uuid.uuid5(uuid.NAMESPACE_X500, app.config['APP_PATH'] + 'admin')
            user_datastore.create_user(
                email='admin',
                password='cta',
                pid=str(pid),
                active=True,
                roles=['admin'],
            )
        # Create demo user
        if not user_datastore.get_user('user'):
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
# Create Admin pages


# Customized User model for SQL-Admin
class UserView(sqla.ModelView):
    searchable_columns = ('email',)
    column_exclude_list = ('password',)
    # form_excluded_columns = ('password',)
    column_auto_select_related = True
    form_overrides = dict(password=PasswordField)
    def is_accessible(self):
        return current_user.has_role('admin')


# Customized Role model for SQL-Admin
class RoleView(sqla.ModelView):
    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role('admin')

# Initialize Flask-Admin
admin = Admin(app, template_mode='bootstrap3', url='/admin')

# Add Flask-Admin views for Users and Roles
admin.add_view(UserView(User, db.session))
admin.add_view(RoleView(Role, db.session))


# ----------
# Manage user accounts using flask_security (flask_login)


@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    logger.info(user.email)
    #session['server_url'] = app.config['UWS_SERVER_URL_JS']
    session['auth'] = base64.b64encode(current_user.email + ':' + str(current_user.pid))
    flash('"{}" is now logged in'.format(user.email), 'info')


@user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    logger.info(user.email)
    flash('"{}" is now logged out'.format(user.email), 'info')


@app.route('/accounts/profile', methods=['GET', 'POST'])
@login_required
def profile():
    logger.debug(current_user.__dict__)
    order = ['email', 'pid']
    profile = {
        'email': {
            'value': current_user.email,
            'label': 'Username or Email Address',
            'description': '',
            'disabled': True
        },
        'pid': {
            'value': current_user.pid,
            'label': 'PID',
            'description': 'Persistent ID of the user on the UWS server',
        }

    }
    if request.method == 'POST':
        pid = request.form.get('pid')
        if pid:
            if pid != current_user.pid:
                current_user.pid = pid
                user_datastore.put(current_user)
                user_datastore.commit()
                logger.debug(current_user.__dict__)
                flash('PID of user {} has been updated'.format(current_user.email))
        else:
            flash('No PID found in form')
        return redirect(url_for('profile'), 303)
    return render_template('profile.html', order=order, profile=profile)


@app.route('/preferences', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def preferences():
    if request.method == 'POST':
        logger.debug('Modify editable config')
        for key, value in request.form.iteritems():
            if key in EDITABLE_CONFIG:
                app.config[key] = str(value)
        logger.debug({k: app.config[k] for k in EDITABLE_CONFIG.keys() if k in app.config})
        save_config()
        flash('Preferences successfully updated', 'info')
        return redirect(url_for('preferences'), 303)
    return render_template('preferences.html')


# ----------
# Web Pages


@app.context_processor
def add_url_to_context():
    return dict(url=request.url)


@app.route('/')
def home():
    """Home page"""
    # logger.debug('app.config = {}'.format(app.config))
    logger.debug({k: app.config[k] for k in EDITABLE_CONFIG.keys() if k in app.config})
    logger.debug('g = {}'.format(g.__dict__))
    logger.info('session = {}'.format(session.__dict__))
    return render_template('home.html')


@app.route('/job_list', defaults={'jobname': ''})
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
@app.route('/job_definition/', methods=['GET', 'POST'], defaults={'jobname': ''})
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
    logger.debug(app.config['UWS_SERVER_URL'])
    # Add auth information (Basic, Token...)
    auth = None
    if app.config['UWS_AUTH'] == 'Basic':
        auth = HTTPBasicAuth(current_user.email, current_user.pid)
    # Send request
    if method == 'POST':
        r = requests.post('{}{}'.format(app.config['UWS_SERVER_URL'], uri), data=data, auth=auth)
    else:
        r = requests.get('{}{}'.format(app.config['UWS_SERVER_URL'], uri), params=params, auth=auth)
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
