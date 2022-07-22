#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
UWS client implementation using bottle.py and javascript
"""

import subprocess
import yaml
import uuid
import datetime
import base64
import requests
import json
from requests.auth import HTTPBasicAuth
import logging
import logging.config
from flask import Flask, request, abort, redirect, url_for, session, g, current_app, render_template, flash, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, roles_required, utils, hash_password
from flask_security.forms import LoginForm, RegisterForm
from flask_login import user_logged_in, user_logged_out, current_user, LoginManager, login_user, logout_user
from authlib.integrations.flask_client import OAuth
from flask_security import AnonymousUser
from flask_security.core import (
    _user_loader as _flask_security_user_loader,
    _request_loader as _flask_security_request_loader)
from flask_security.utils import config_value as security_config_value
from flask_admin import Admin
from flask_admin.contrib import sqla
from flask_mail import Mail
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired
from .settings import *


# Set logger
logging.config.dictConfig(LOGGING)
logger = logging.getLogger('uws_client')
logger.debug('Load flask client')

# Create var dirs if not exist
for p in [VAR_PATH + '/logs', VAR_PATH + '/config', VAR_PATH + '/db']:
    if not os.path.isdir(p):
        os.makedirs(p)


# Return the git revision as a string
def git_version():
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {'PATH': '/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin:/root/bin'}
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env, cwd=APP_PATH).communicate()[0]
        return out

    try:
        # out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        out = _minimal_ext_cmd(['git', 'log', '-1', '--format=%H'])
        if not out:
            logger.warning("Revision id not found, try to read git logs directly")
            out = _minimal_ext_cmd(['tail', '-1', '.git/logs/HEAD'])
            out = out.split(" ")[1]
        GIT_REVISION = out.strip().decode('ascii')
        out = _minimal_ext_cmd(['git', 'log', '-1', '--date=short', '--format=%cd'])
        if not out:
            logger.warning("Revision date not found, try to get from index")
            out = _minimal_ext_cmd(['date', '-r', '.git/index', '+"%Y-%m-%d"'])
        GIT_DATE = out.strip().decode('ascii')
    except Exception as e:
        logger.warning(str(e))
        GIT_REVISION = "Unknown"
        GIT_DATE = "Unknown"

    return GIT_DATE, GIT_REVISION


# ----------
# create the application instance :)


app = Flask(__name__, instance_relative_config=True, instance_path=VAR_PATH)
app.secret_key = b'\ttrLu\xdd\xde\x9f\xd2}\xc1\x0e\xb6\xe6}\x95\xc6\xb1\x8f\xa09\xf5\x1aG'
# app.config.update(EDITABLE_CONFIG)  # Default editable config
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object(__name__)  # load config from this file

mail = Mail(app)


# ----------
# User DB


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


def gen_token(context):
    try:
        email = context.current_parameters.get('email')
        token = uuid.uuid5(uuid.NAMESPACE_X500, app.config['APP_PATH'] + email)
    except:
        token = uuid.uuid4()
    return str(token)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    # username = db.Column(db.String(255), unique=True, index=True)
    password = db.Column(db.String(255))
    token = db.Column(db.String(255), default=gen_token)
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False, default=gen_token)
    confirmed_at = db.Column(db.DateTime(), default=datetime.datetime.now)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return self.email


class ExtendedLoginForm(LoginForm):
    email = StringField('Username or Email Address', [InputRequired()])


class ExtendedRegisterForm(RegisterForm):
    email = StringField('Username or Email Address', [InputRequired()])


def get_or_create(db_session, model, **kwargs):
    instance = db_session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db_session.add(instance)
        db_session.commit()
        return instance


user_datastore = SQLAlchemyUserDatastore(db, User, Role)

security = Security(app, user_datastore,
                    login_form=ExtendedLoginForm, register_form=ExtendedRegisterForm)
#                 login_manager=_get_login_manager(app, anonymous_user=None))


# Setup Flask-Security with OIDC (authlib)

# https://flask-security-too.readthedocs.io/en/stable/customizing.html#authorization-with-oauth2 -> complex...
# https://realpython.com/flask-google-login/
# https://www.codeflow.site/fr/article/flask-google-login -> almost, but issue with prepare_token_request (client_id should not appear in request body)
# https://github.com/authlib/demo-oauth-client/blob/master/flask-google-login/app.py -> works smoothly !

oauth = OAuth(app)
idp_names = dict((idp['title'], i) for i, idp in enumerate(OIDC_IDPS))
for idp in OIDC_IDPS:
    oauth.register(
        name=idp["title"],
        client_id=idp["client_id"],
        client_secret=idp["client_secret"],
        server_metadata_url=idp["url"],
        client_kwargs={
            'scope': idp["scope"]
        }
    )
logger.debug("OIDC clients loaded: " + str(oauth._clients.keys()))

@app.route('/accounts/oidc/login', defaults={'idp': ""})
@app.route('/accounts/oidc/login/', defaults={'idp': ""})
@app.route('/accounts/oidc/login/<idp>')
def oidc_login(idp):
    if idp in idp_names:
        session["oidc_idp"] = idp
        logger.debug("Use OIDC IdP " + idp)
    else:
        flash("This OIDC Identity Provider has not been defined: " + idp, "warning")
        return redirect(url_for('home'), 303)
    redirect_uri = url_for('oidc_callback', _external=True)  # , idp=idp)
    return oauth._clients[session["oidc_idp"]].authorize_redirect(redirect_uri)


@app.route('/accounts/oidc/callback')  # , defaults={'idp': 0})
# @app.route('/accounts/oidc/callback/<idp>')
def oidc_callback():
    if "oidc_idp" not in session:
        flash("No OIDC Identity Provider has been defined.", "warning")
        return redirect(url_for('home'), 303)
    elif session["oidc_idp"] not in idp_names:
        flash("This OIDC Identity Provider has not been defined: " + session["oidc_idp"], "warning")
        return redirect(url_for('home'), 303)
    # Store token
    token = oauth._clients[session["oidc_idp"]].authorize_access_token()
    # session['oidc_access_token'] = token.get('access_token')
    logger.debug("token = " + str(token))
    # Get userinfo
    # user = token.get('userinfo')  # use direct userinfo sent with token (not always present...)
    user = oauth._clients[session["oidc_idp"]].userinfo()
    session['oidc_user'] = user
    logger.debug("user = " + str(user))
    # Get email, or sub if email is not present (sub is always returned)
    oidc_email = user.get("email", None).lower()
    if not oidc_email:
        logger.warning("No email was found for user. Using \"sub\" to identify user")
        oidc_email = user["sub"]
    # Check if user exists in the database.
    oidc_user = user_datastore.find_user(email=oidc_email)
    if not oidc_user:
        user_datastore.create_user(
            email=oidc_email,
            active=True,
            roles=['user', 'oidc', 'job_definition', 'job_list'],
        )
        db.session.commit()
        oidc_user = user_datastore.find_user(email=oidc_email)
        logger.info('OIDC user {} is new and was added'.format(oidc_email))
    else:
        logger.info('user {} found in local user database'.format(oidc_email))
    # Begin user session by logging the user in
    login_user(oidc_user)
    # Send user back to homepage
    return redirect(url_for("home"))


@app.route('/accounts/oidc/logout')
def oidc_logout():
    if "oidc_idp" not in session:
        flash("No OIDC Identity Provider has been defined.", "warning")
        return redirect(url_for('home'), 303)
    elif session["oidc_idp"] not in idp_names:
        flash("This OIDC Identity Provider has not been defined: " + session["oidc_idp"], "warning")
        return redirect(url_for('home'), 303)
    # Revoke token on OIDC IdP
    server_metadata = oauth._clients[session["oidc_idp"]].load_server_metadata()
    revoke_url = server_metadata.get('revocation_endpoint', None)
    if revoke_url:
        oauth_client = oauth._clients[session["oidc_idp"]]._get_oauth_client()
        resp = oauth_client.revoke_token(revoke_url)
        # , token=session['oidc_access_token'], token_type_hint="access_token", body=None, auth=None, headers=None)
        # example: client.revoke_token(app.config['OASERVER'] + '/oauth2/revoke', token=session['oatoken']['access_token'])
        logger.info("OIDC token revoked on IdP " + session["oidc_idp"])
        logger.info(resp)
    else:
        logger.info("No revocation_endpoint for OIDC Idp " + session["oidc_idp"])
    # Logout user locally
    logout_user()
    return redirect(url_for("home"))


# ----------
# Load/store editable config


@app.before_first_request
def load_config():
    logger.debug('Load editable config')
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as cf:
            econf = yaml.safe_load(cf)
            app.config.update(econf)
    else:
        save_config()


def save_config():
    logger.debug('Save editable config')
    with open(CONFIG_FILE, 'w') as cf:
        econf = {k: app.config[k] for k in EDITABLE_CONFIG if k in app.config}
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
            name='oidc',
            description='User from OIDC',
        )
        user_datastore.find_or_create_role(
            name='user',
            description='User',
        )
        user_datastore.find_or_create_role(
            name='admin',
            description='Administrator',
        )
        user_datastore.find_or_create_role(
            name='job_definition',
            description='Access to job definition',
        )
        user_datastore.find_or_create_role(
            name='job_list',
            description='Access to job list',
        )
        # Create admin user
        if not user_datastore.find_user(id=ADMIN_NAME):
            user_datastore.create_user(
                email=ADMIN_NAME,
                password=hash_password(ADMIN_DEFAULT_PW),
                active=True,
                roles=['admin', 'job_definition', 'job_list'],
            )
        # Create demo user
        if not user_datastore.find_user(id=TESTUSER_NAME):
            user_datastore.create_user(
                email=TESTUSER_NAME,
                password=hash_password(TESTUSER_DEFAULT_PW),
                active=True,
                roles=['user', 'job_definition', 'job_list'],
            )
        db.session.commit()
        logger.debug('Database created or updated')
    except Exception as e:
        db.session.rollback()
        logger.warning(str(e))


# ----------
# Create Admin pages


# Customized User model for SQL-Admin
class UserView(sqla.ModelView):
    column_searchable_list = ('email',)
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

# Add Flask-Admin views_old for Users and Roles
admin.add_view(UserView(User, db.session))
admin.add_view(RoleView(Role, db.session))


# ----------
# Manage user accounts using flask_security (flask_login)


@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    logger.info(user.email + " (" + session.get("oidc_idp", "Local") + ")")
    #session['server_url'] = app.config['UWS_SERVER_URL_JS']
    session['auth'] = base64.b64encode((current_user.email + ':' + str(current_user.token)).encode())
    # quick request to server (will create user on server)
    response = uws_server_request('jdl', method='GET')
    flash('"{}" is now logged in'.format(user.email), 'info')


@user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    logger.info(user.email)
    flash('"{}" is now logged out'.format(user.email), 'info')
    session.clear()


@app.route('/accounts/profile', methods=['GET', 'POST'])
@login_required
def profile():
    logger.debug(current_user.__dict__)
    order = ['email', 'token']
    profile = {
        'email': {
            'value': current_user.email,
            'label': 'Username or Email Address',
            'description': '',
            'disabled': True
        },
        'token': {
            'value': current_user.token,
            'label': 'Token',
            'description': 'Persistent ID of the user on the UWS server',
        }

    }
    if request.method == 'POST':
        token = request.form.get('token')
        if token:
            if token != current_user.token:
                current_user.token = token
                user_datastore.put(current_user)
                user_datastore.commit()
                logger.debug(current_user.__dict__)
                flash('Token of user {} has been updated'.format(current_user.email))
        else:
            flash('No token found in form')
        return redirect(url_for('profile'), 303)
    return render_template('profile.html', order=order, profile=profile)


@app.route('/admin/preferences', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def preferences():
    if request.method == 'POST':
        logger.debug('Modify editable config')
        for key, value in request.form.items():
            if key in EDITABLE_CONFIG:
                app.config[key] = str(value)
        save_config()
        flash('Preferences successfully updated', 'info')
        return redirect(url_for('preferences'), 303)
    return render_template('preferences.html')


@app.route('/admin/server_accounts', methods=['GET'])
@login_required
@roles_required('admin')
def server_accounts():
    # Get users from server
    return render_template('server_accounts.html')


@app.route('/admin/add_client_user', methods=['POST'])
@login_required
@roles_required('admin')
def import_server_account():
    email = request.form.get('name', None)
    token = request.form.get('token', None)
    if email and token:
        if not user_datastore.find_user(email=email):
            user = user_datastore.create_user(
                email=email,
                token=token,
                active=True,
                roles=['user'],
            )
            db.session.commit()
            logger.info('User {} added'.format(email))
            flash('User added, please enter new password and save record', 'success')
            return user.get_id(), 200
        # Already exist
        logger.warning('Cannot create user (already exists)')
        abort(409)
    else:
        # Missing email/token
        logger.warning('Cannot create user (missing email/token)')
        abort(400)


@app.route('/admin/server_jobs', methods=['GET'])
@login_required
@roles_required('admin')
def server_jobs():
    # Get jobs from server
    return render_template('server_jobs.html')


# ----------
# Web Pages


@app.context_processor
def add_url_to_context():
    return dict(url=request.url)


@app.route('/')
def home():
    """Home page"""
    # logger.debug('app.config = {}'.format(app.config))
    logger.debug('session = {}'.format(session.__str__()))
    logger.debug('config = '.format({k: app.config[k] for k in EDITABLE_CONFIG if k in app.config}))
    logger.debug('g = {}'.format(g.__dict__))
    date, version = git_version()
    return render_template('home.html', git_date=date, git_version=version)


@app.route('/jobs', defaults={'jobname': ''})
@app.route('/jobs/', defaults={'jobname': ''})
@app.route('/jobs/<jobname>')
#@login_required
def job_list(jobname):
    """Job list page"""
    logger.info(jobname)
    return render_template('job_list.html', jobname=jobname)


@app.route('/job_edit/<jobname>/<jobid>')
#@login_required
def job_edit(jobname, jobid):
    """Job edit page"""
    logger.info(jobname + ' ' + jobid)
    return render_template('job_edit.html', jobname=jobname, jobid=jobid)


@app.route('/job_form/<jobname>')
#@login_required
def job_form(jobname):
    """Job edit page"""
    logger.info(jobname)
    return render_template('job_form.html', jobname=jobname, init_params=json.dumps(request.args.to_dict(flat=False)))


@app.route('/job_definition', methods=['GET', 'POST'], defaults={'jobname': ''})
@app.route('/job_definition/', methods=['GET', 'POST'], defaults={'jobname': ''})
@app.route('/job_definition/<path:jobname>', methods=['GET'])
def job_definition(jobname):
    """Show form for new job definition"""
    logger.info(jobname)
    # No need to authenticate, users can propose new jobs that will be validated
    # if request.method == 'POST':
    #     jobname = request.form.get('name').split('/')[-1]
    #     logger.info('Create new/{}'.format(jobname))
    #     response = uws_server_request('/jdl', method='POST', init_request=request)
    #     if response.status_code == 200:
    #         flash('New job definition has been saved as new/{}'.format(jobname), 'info')
    #         return redirect(url_for('job_definition', jobname='new/{}'.format(jobname)), 303)
    #     else:
    #         flash('Error during creation of job definition for {jn}'.format(jn=jobname),
    #           category='danger')
    # Show form
    # Set is_admin (will show validate buttons)
    is_admin = False
    if current_user.is_authenticated and current_user.has_role('admin'):
        is_admin = True
    return render_template('job_definition.html', jobname=jobname, is_admin=is_admin)


# @app.route('/jdl/import_jdl', methods=['POST'])
# @login_required
# def import_jdl():
#     """Validate job on server"""
#     # Send request to UWS Server
#     response = uws_server_request('/jdl/import_jdl', method='POST', init_request=request)
#     # redirect to job_definition with message
#     if response.status_code == 200:
#         jobname = response.json().get('jobname', None)
#         if jobname:
#             flash('Job definition has been imported as "new/{jn}"'.format(jn=jobname))
#             return redirect(url_for('job_definition', jobname='new/' + jobname), 303)
#     flash('Error during import of job definition', category='danger')
#     return redirect(url_for('job_definition'), 303)


# @app.route('/jdl/<path:jobname>/validate')
# @login_required
# @roles_required('admin')
# def validate_jdl(jobname):
#     """Validate job on server"""
#     logger.info(jobname)
#     # Send request to UWS Server
#     response = uws_server_request('/jdl/{}/validate'.format(jobname), method='POST', init_request=request)
#     # redirect to job_definition with message
#     if response.status_code == 200:
#         flash('Job definition for new/{jn} has been validated and renamed {jn}'.format(jn=jobname), category='success')
#         return redirect(url_for('job_definition', jobname=jobname), 303)
#     elif response.status_code == 403:
#         flash('Forbidden: insufficient rights to validate job definition for new/{jn}'.format(jn=jobname), category='warning')
#     else:
#         flash('Error during validation of job definition for {jn}'.format(jn=jobname), category='danger')
#     return redirect(url_for('job_definition', jobname='new/' + jobname), 303)


# @app.route('/jdl/<path:jobname>/copy_script')
# @login_required
# @roles_required('admin')
# def cp_script(jobname):
#     """Copy job script to work server"""
#     logger.info(jobname)
#     # Send request to UWS Server
#     response = uws_server_request('/jdl/{}/copy_script'.format(jobname), method='POST', init_request=request)
#     # redirect to job_definition with message
#     if response.status_code == 200:
#         flash('Job script {}.sh has been copied to work cluster'.format(jobname))
#     else:
#         flash('Job definition for {jn} was not found on the server. Cannot validate.'.format(jn=jobname))
#     return redirect(url_for('job_definition', jobname=jobname), 303)


# ----------
# Proxy (to avoid cross domain calls and add Auth header)


@app.route('/proxy/<path:uri>', methods=['GET', 'POST', 'DELETE'])
def proxy(uri):
    response = uws_server_request('/' + uri, method=request.method, init_request=request)
    #logger.debug(response.headers.__dict__)
    # def generate():
    #     for chunk in r.iter_content(CHUNK_SIZE):
    #         yield chunk
    # return Response(stream_with_context(generate()), content_type = r.headers['content-type'])
    headers = {}
    for k in ['content-length', 'content-disposition']:  #, 'content-encoding']:
        if k in response.headers.__dict__['_store']:
            headers[k] = response.headers[k]
    return Response(response, status=response.status_code, content_type=response.headers.get('content-type', None), headers=headers)


def uws_server_request(uri, method='GET', init_request=None):
    server_url = app.config['UWS_SERVER_URL']
    # Remove server_url from uri if present (uri is expected to be a relative path)
    uri = uri.replace(server_url, '')
    # Add auth information (Basic, Token...)
    auth = None
    if app.config['UWS_AUTH'] == 'Basic':
        if current_user.is_authenticated:
            auth = HTTPBasicAuth(current_user.email, current_user.token)
        else:
            auth = HTTPBasicAuth('anonymous', 'anonymous')
    # Send request
    if method == 'DELETE':
        response = requests.delete('{}{}'.format(server_url, uri), auth=auth)
    elif method == 'POST':
        post={}
        if init_request:
            for key in list(init_request.form.keys()):
                value = init_request.form.getlist(key)
                logger.debug('POST {}: {}'.format(key, value))
                if len(value) == 1:
                    post[key] = value[0]
                else:
                    post[key] = value
        files = {}
        if init_request:
            for fname in list(init_request.files.keys()):
                logger.debug('file: ' + fname)
                fp = init_request.files[fname]
                files[fname] = (fp.filename, fp.stream, fp.content_type, fp.headers)
        response = requests.post('{}{}'.format(server_url, uri), data=post, files=files, auth=auth)
    else:
        params = {}
        if init_request:
            params = init_request.args
        response = requests.get('{}{}'.format(server_url, uri), params=params, auth=auth)
    # Return response
    logger.info("{} {}{} ({})".format(method, server_url, uri, response.status_code))
    return response


# ----------
# run server


if __name__ == '__main__':
    # Run local web server
    #run(app, host='localhost', port=8080, debug=False, reloader=True)
    app.run(host='localhost', port=8080, debug=True)
    pass
