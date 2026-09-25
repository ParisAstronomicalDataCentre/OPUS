#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
UWS client implementation using flask and javascript
"""

import datetime
import json
import subprocess
from urllib.parse import urlencode
import os

import requests
import yaml
from authlib.integrations.flask_client import OAuth
from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_admin import Admin
from flask_admin.contrib import sqla
from flask_login import (
    current_user,
    login_user,
    logout_user,
    user_logged_in,
    user_logged_out,
)
from flask_mail import Mail
from flask_security import (
    RoleMixin,
    Security,
    SQLAlchemyUserDatastore,
    UserMixin,
    hash_password,
    login_required,
    roles_required,
    user_authenticated,
)
from flask_security.forms import LoginForm, RegisterFormV2, unique_user_email
from flask_sqlalchemy import SQLAlchemy
from requests.auth import HTTPBasicAuth
from wtforms import PasswordField, StringField
from wtforms.validators import InputRequired

from opus_config import logs

from .settings import (
    settings,
    APP_PATH,
    EDITABLE_CONFIG,
    logger,
)

# ----------
# Helper functions


# Return the git revision as a string
def git_version():
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {
            "PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin:/root/bin"
        }
        out = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, env=env, cwd=APP_PATH
        ).communicate()[0]
        return out

    try:
        # out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        out = _minimal_ext_cmd(["git", "log", "-1", "--format=%H"])
        if not out:
            logger.warning("Revision id not found, try to read git logs directly")
            out = _minimal_ext_cmd(["tail", "-1", ".git/logs/HEAD"])
            out = out.split(" ")[1]
        GIT_REVISION = out.strip().decode("ascii")
        out = _minimal_ext_cmd(["git", "log", "-1", "--date=short", "--format=%cd"])
        if not out:
            logger.warning("Revision date not found, try to get from index")
            out = _minimal_ext_cmd(["date", "-r", ".git/index", '+"%Y-%m-%d"'])
        GIT_DATE = out.strip().decode("ascii")
    except Exception as e:
        logger.warning(str(e))
        GIT_REVISION = "Unknown"
        GIT_DATE = "Unknown"

    return GIT_DATE, GIT_REVISION


# ----------
# Create the application instance :)


app = Flask(__name__, instance_relative_config=True, instance_path=settings.VAR_PATH)
app.secret_key = settings.SECRET_KEY.get_secret_value()
# app.config.update(EDITABLE_CONFIG)  # Default editable config
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object("uws_client.settings")  # Flask-Security config and EDITABLE_CONFIG
app.config.from_mapping(settings.export())  # settings (see opus_config/client.py)

mail = Mail(app)


# ----------
# Load/store editable config


def load_config():
    if os.path.isfile(settings.CONFIG_FILE):
        with open(settings.CONFIG_FILE) as cf:
            econf = yaml.safe_load(cf)
            app.config.update(econf)
        logger.info("Loading editable config: " + repr(econf))
    else:
        save_config()


# Editable config values from settings files, only values that differ are stored
# in CONFIG_FILE (so that a change in settings_local.py is not hidden by CONFIG_FILE)
SETTINGS_CONFIG = {k: app.config[k] for k in EDITABLE_CONFIG if k in app.config}


def save_config():
    logger.info("Saving editable config")
    with open(settings.CONFIG_FILE, "w") as cf:
        econf = {
            k: app.config[k]
            for k in EDITABLE_CONFIG
            if k in app.config and app.config[k] != SETTINGS_CONFIG.get(k)
        }
        yaml.dump(econf, cf, default_flow_style=False)


def update_config(key, value):
    if key in EDITABLE_CONFIG:
        app.config[key] = value
        save_config()


# Loads editable config at app start (before_first_request):
with app.app_context():
    load_config()


# ----------
# User DB


db = SQLAlchemy(app)


# Define models for User and Role
roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return self.name


def gen_token(context):
    # Random by default (see TOKEN_GEN setting), must not be predictable: the token is
    # used to authenticate the user on the server, and fs_uniquifier in the session
    return settings.new_token(context)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    # username = db.Column(db.String(255), unique=True, index=True)
    password = db.Column(db.String(255))
    token = db.Column(db.String(255), default=gen_token)
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(
        db.String(255), unique=True, nullable=False, default=gen_token
    )
    confirmed_at = db.Column(db.DateTime(), default=datetime.datetime.now)
    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )

    def __init__(self, **kwargs):
        # token set at creation (the column default is only applied when the user is saved): at
        # registration, the user is logged in, and its account created on the server, before
        kwargs.setdefault("token", gen_token(None))
        super().__init__(**kwargs)

    def __repr__(self):
        return self.email

    def get_id_db(self):
        return self.id



class OIDCToken(db.Model):
    """OpenID Connect tokens of a user signed in with an Identity Provider (kept on the client,
    never sent to the browser), used to call the server with UWS_AUTH = "OIDC" """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True)
    idp = db.Column(db.String(255))
    token = db.Column(db.Text)  # JSON: access_token, refresh_token, expires_at...


class ExtendedLoginForm(LoginForm):
    email = StringField("Username or Email Address", [InputRequired()])


class ExtendedRegisterForm(RegisterFormV2):
    # a user name is accepted (not only an email address), not already used
    email = StringField("Username or Email Address", [InputRequired(), unique_user_email])


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

security = Security(
    app,
    user_datastore,
    login_form=ExtendedLoginForm,
    register_form=ExtendedRegisterForm,
)
#                 login_manager=_get_login_manager(app, anonymous_user=None))


# Setup Flask-Security with OIDC (authlib)

# https://flask-security-too.readthedocs.io/en/stable/customizing.html#authorization-with-oauth2 -> complex...
# https://realpython.com/flask-google-login/
# https://www.codeflow.site/fr/article/flask-google-login -> almost, but issue with prepare_token_request (client_id should not appear in request body)
# https://github.com/authlib/demo-oauth-client/blob/master/flask-google-login/app.py -> works smoothly !

oauth = OAuth(app)
idp_names = {idp["title"]: i for i, idp in enumerate(settings.OIDC_IDPS)}
for idp in settings.OIDC_IDPS:
    oauth.register(
        name=idp["title"],
        client_id=idp["client_id"],
        client_secret=idp["client_secret"],
        server_metadata_url=idp["url"],
        client_kwargs={"scope": idp["scope"]},
    )
logger.debug("OIDC clients loaded: " + str(oauth._clients.keys()))


@app.route("/accounts/oidc/login", defaults={"idp": ""})
@app.route("/accounts/oidc/login/", defaults={"idp": ""})
@app.route("/accounts/oidc/login/<idp>")
def oidc_login(idp):
    if idp in idp_names:
        session["oidc_idp"] = idp
        logger.debug("Use OIDC IdP " + idp)
    else:
        flash("This OIDC Identity Provider has not been defined: " + idp, "warning")
        return redirect(url_for("home"), 303)
    redirect_uri = url_for("oidc_callback", _external=True)  # , idp=idp)
    # Audience of the access token, required by the server if defined for this Identity Provider
    audience = settings.OIDC_IDPS[idp_names[idp]].get("audience")
    kwargs = {"audience": audience} if audience else {}
    return oauth._clients[session["oidc_idp"]].authorize_redirect(redirect_uri, **kwargs)


@app.route("/accounts/oidc/callback")  # , defaults={'idp': 0})
# @app.route('/accounts/oidc/callback/<idp>')
def oidc_callback():
    if "oidc_idp" not in session:
        flash("No OIDC Identity Provider has been defined.", "warning")
        return redirect(url_for("home"), 303)
    elif session["oidc_idp"] not in idp_names:
        flash(
            "This OIDC Identity Provider has not been defined: " + session["oidc_idp"],
            "warning",
        )
        return redirect(url_for("home"), 303)
    # Get the token (access, refresh and id tokens are secrets: never log them)
    token = oauth._clients[session["oidc_idp"]].authorize_access_token()
    # Get userinfo
    # user = token.get('userinfo')  # use direct userinfo sent with token (not always present...)
    user = oauth._clients[session["oidc_idp"]].userinfo()
    session["oidc_user"] = user
    logger.debug(f"OIDC userinfo from {session['oidc_idp']} for sub={user.get('sub')}")
    # Get email, or sub if email is not present (sub is always returned)
    email = (user.get("email") or "").lower()
    email_verified = str(user.get("email_verified")).lower()  # "true", "false" or "none" (not given)
    if email and email_verified == "false":
        logger.warning(f"OIDC login refused for {email}: email not verified by the Identity Provider")
        flash("Your email is not verified by the Identity Provider, cannot sign in.", "warning")
        return redirect(url_for("home"), 303)
    oidc_email = email
    if not oidc_email:
        logger.warning('No email was found for user. Using "sub" to identify user')
        oidc_email = user["sub"]
    # Check if user exists in the database.
    oidc_user = user_datastore.find_user(email=oidc_email)
    if oidc_user and not oidc_user.has_role("oidc") and email_verified != "true":
        # A local account (not created from OIDC) is only used if the Identity Provider verified the email
        logger.warning(f"OIDC login refused for {oidc_email}: local account, and email not verified")
        flash(
            "A local account exists with this email, and the Identity Provider did not verify the email: "
            "cannot sign in with this Identity Provider.",
            "warning",
        )
        return redirect(url_for("home"), 303)
    if not oidc_user:
        user_datastore.create_user(
            email=oidc_email,
            active=True,
            roles=["user", "oidc"],
        )
        db.session.commit()
        oidc_user = user_datastore.find_user(email=oidc_email)
        logger.info(f"OIDC user {oidc_email} is new and was added")
    else:
        logger.info(f"user {oidc_email} found in local user database")
    # Keep the tokens before the login (the first request to the server is sent at login)
    save_oidc_token(oidc_user, session["oidc_idp"], token)
    # Begin user session by logging the user in
    login_user(oidc_user)
    # Send user back to homepage
    return redirect(url_for("home"))


@app.route("/accounts/oidc/logout")
def oidc_logout():
    # Before the local logout (which revokes and removes the tokens, see on_user_logged_out):
    # URL ending the session of the user on the Identity Provider, if any
    idp_logout_url = oidc_idp_logout_url()
    # The user is always logged out, even if the Identity Provider cannot be reached
    logout_user()
    return redirect(idp_logout_url or url_for("home"))


def oidc_idp_logout_url():
    """URL ending the session of the user on the Identity Provider, or None

    - if the Identity Provider has an end_session_endpoint: RP-initiated logout (standard), the
      user is then redirected to the home page of the client (post_logout_redirect_uri, to be
      registered on the Identity Provider)
    - else, if defined for the Identity Provider in OIDC_IDPS (not by default): "logout_url",
      e.g. https://<iam>/logout for INDIGO-IAM, where the user stays
    Ending the session on the Identity Provider logs the user out of all the applications using
    this Identity Provider (single sign-on).
    """
    if not current_user.is_authenticated:
        return None
    row = OIDCToken.query.filter_by(user_id=current_user.id).first()
    idp_name = row.idp if row else session.get("oidc_idp")
    if idp_name not in idp_names:
        return None
    idp = settings.OIDC_IDPS[idp_names[idp_name]]
    try:
        end_session = oauth._clients[idp_name].load_server_metadata().get("end_session_endpoint")
    except Exception as e:
        logger.warning(f"Cannot get the metadata of OIDC IdP {idp_name}: {type(e).__name__}")
        end_session = None
    if end_session:
        params = {"post_logout_redirect_uri": url_for("home", _external=True), "client_id": idp["client_id"]}
        id_token = json.loads(row.token).get("id_token") if row else None
        if id_token:
            params["id_token_hint"] = id_token
        return end_session + ("&" if "?" in end_session else "?") + urlencode(params)
    return idp.get("logout_url") or None


def revoke_oidc_tokens(user):
    """Revoke the tokens of the user on the Identity Provider, if it has a revocation endpoint"""
    row = OIDCToken.query.filter_by(user_id=user.id).first()
    if not row or row.idp not in idp_names:
        return
    token = json.loads(row.token)
    try:
        client = oauth._clients[row.idp]
        revoke_url = client.load_server_metadata().get("revocation_endpoint")
        if not revoke_url:
            logger.info(f"No revocation_endpoint for OIDC IdP {row.idp}")
            return
        oauth_client = client._get_oauth_client()
        # the refresh token first (the access tokens obtained with it are then also revoked)
        for hint in ("refresh_token", "access_token"):
            if token.get(hint):
                oauth_client.revoke_token(revoke_url, token=token[hint], token_type_hint=hint)
        logger.info(f"OIDC tokens of {user.email} revoked on IdP {row.idp}")
    except Exception as e:
        logger.warning(f"Cannot revoke the OIDC tokens of {user.email} on IdP {row.idp}: {type(e).__name__}")


# ----------
# Create default database


def create_db():
    try:
        db.create_all()
        user_datastore.find_or_create_role(
            name="oidc",
            description="User from OIDC",
        )
        user_datastore.find_or_create_role(
            name="user",
            description="User",
        )
        user_datastore.find_or_create_role(
            name="admin",
            description="Administrator",
        )
        # Roles of previous versions, not used: remove them
        for name in ["job_definition", "job_list"]:
            role = user_datastore.find_role(name)
            if role:
                for user in list(role.users):
                    user_datastore.remove_role_from_user(user, role)
                user_datastore.delete(role)
                logger.info(f"Unused role removed: {name}")
        # Create admin user if not found
        if not user_datastore.find_user(email=settings.ADMIN_NAME):
            user_datastore.create_user(
                email=settings.ADMIN_NAME,
                password=hash_password(settings.ADMIN_DEFAULT_PW.get_secret_value()),
                token=settings.ADMIN_TOKEN.get_secret_value(),
                active=True,
                roles=["admin"],
            )
            logger.info("Add user to db: " + settings.ADMIN_NAME)
        # Create test user if not found
        if not user_datastore.find_user(email=settings.TESTUSER_NAME):
            user_datastore.create_user(
                email=settings.TESTUSER_NAME,
                password=hash_password(settings.TESTUSER_DEFAULT_PW.get_secret_value()),
                active=True,
                roles=["user"],
            )
            logger.info("Add user to db: " + settings.TESTUSER_NAME)
        db.session.commit()
        logger.debug("Database created or updated")
    except Exception as e:
        db.session.rollback()
        logger.warning(str(e))


# Create or Update DB at app start (before_first_request):
with app.app_context():
    create_db()


# ----------
# Create Admin pages


# Customized User model for SQL-Admin
class UserView(sqla.ModelView):
    column_searchable_list = ("email",)
    column_exclude_list = ("password",)
    # form_excluded_columns = ('password',)
    column_auto_select_related = True
    form_overrides = {"password": PasswordField}

    def is_accessible(self):
        return current_user.has_role("admin")


# Customized Role model for SQL-Admin
class RoleView(sqla.ModelView):
    # Prevent administration of Roles unless the currently logged-in user has the "admin" role

    def is_accessible(self):
        return current_user.has_role("admin")


# Initialize Flask-Admin
admin = Admin(app, url="/admin")  # removed for Py3.13: , template_mode='bootstrap3'

# Add Flask-Admin views_old for Users and Roles
admin.add_view(UserView(User, db))
admin.add_view(RoleView(Role, db))


# ----------
# Manage user accounts using flask_security (flask_login)


@user_authenticated.connect_via(app)
def on_user_authenticated(sender, user, authn_via=None, **kwargs):
    # Login with a password (not OIDC): forget the Identity Provider of a previous OIDC login
    # attempt, so that the session is not considered as an OIDC session
    if authn_via and "password" in authn_via:
        session.pop("oidc_idp", None)


@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    logger.info(user.email + " (" + session.get("oidc_idp", "Local") + ")")
    # quick request to server (will create user on server)
    try:
        response = uws_server_request("/jdl", method="GET")
    except requests.exceptions.RequestException as e:
        error_msg = "Server connection error: " + str(e)
        flash(error_msg, "warning")
    flash(f'"{user.email}" is now logged in', "info")


@user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    logger.info(user.email)
    # OIDC tokens of the user: revoked on the Identity Provider, and removed from the client
    revoke_oidc_tokens(user)
    OIDCToken.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    session.clear()
    flash(f'"{user.email}" is now logged out', "info")


@app.route("/accounts/profile", methods=["GET", "POST"])
@login_required
def profile():
    logger.debug(f"Profile of {current_user.email}")
    order = ["email", "token"]
    profile = {
        "email": {
            "value": current_user.email,
            "label": "Username or Email Address",
            "description": "",
            "disabled": True,
        },
        "token": {
            "value": current_user.token,
            "label": "Token",
            "description": "Persistent ID of the user on the UWS server",
        },
    }
    if request.method == "POST":
        token = request.form.get("token")
        if token:
            if token != current_user.token:
                current_user.token = token
                user_datastore.put(current_user)
                user_datastore.commit()
                logger.debug(f"Profile of {current_user.email}")
                flash(f"Token of user {current_user.email} has been updated")
        else:
            flash("No token found in form")
        return redirect(url_for("profile"), 303)
    return render_template("profile.html", order=order, profile=profile)


@app.route("/admin/preferences", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def preferences():
    if request.method == "POST":
        logger.debug("Modify editable config")
        for key, value in request.form.items():
            if key in EDITABLE_CONFIG:
                app.config[key] = str(value)
        save_config()
        flash("Preferences successfully updated", "info")
        return redirect(url_for("preferences"), 303)
    return render_template("preferences.html", defaults=SETTINGS_CONFIG)


@app.route("/admin/server_accounts", methods=["GET"])
@login_required
@roles_required("admin")
def server_accounts():
    # Get users from server
    return render_template("server_accounts.html")


@app.route("/admin/add_client_user", methods=["POST"])
@login_required
@roles_required("admin")
def import_server_account():
    email = request.form.get("name", None)
    token = request.form.get("token", None)
    if email and token:
        if not user_datastore.find_user(email=email):
            user = user_datastore.create_user(
                email=email,
                token=token,
                active=True,
                roles=["user"],
            )
            db.session.commit()
            logger.info(f"User {email} added")
            flash("User added, please enter new password and save record", "success")
            return {"user_id": user.get_id_db()}
        # Already exist
        logger.warning("Cannot create user (already exists)")
        abort(409)
    else:
        # Missing email/token
        logger.warning("Cannot create user (missing email/token)")
        abort(400)


@app.route("/admin/server_jobs", methods=["GET"])
@login_required
@roles_required("admin")
def server_jobs():
    # Get jobs from server
    return render_template("server_jobs.html")


@app.route("/admin/logs", methods=["GET"])
@login_required
@roles_required("admin")
def show_logs():
    """Log viewer: log files of the server and nginx (read through the proxy) and of the client"""
    groups = [
        ("Server", app.config["UWS_SERVER_URL_JS"] + "/log", list(logs.log_files(settings.LOG_PATH, "server"))),
        ("Client", url_for("client_log_text"), list(logs.log_files(settings.LOG_PATH, "client"))),
    ]
    return render_template("show_log.html", groups=groups, selected=request.args.get("file", "server"))


@app.route("/admin/server_log", methods=["GET"])
@app.route("/admin/client_log", methods=["GET"])
def old_log_pages():
    # previous log viewer pages
    return redirect(url_for("show_logs", file=request.path.split("/")[-1].replace("_log", "")))


@app.route("/admin/client_log/text", methods=["GET"])
@login_required
@roles_required("admin")
def client_log_text():
    """Last lines of a log file of the client (same parameters as /log on the server: FILE, LINES)"""
    files = logs.log_files(settings.LOG_PATH, "client", settings.LOG_FILE_SUFFIX)
    name = request.args.get("FILE", "client")
    if name not in files:
        abort(400, f"Unknown log file {name}, available: {', '.join(files)}")
    if not os.path.isfile(files[name]):
        abort(404, f"Log file {name} not found")
    lines = logs.tail(files[name], logs.lines_param(request.args.get("LINES")))
    return Response("\n".join(lines), mimetype="text/plain")


# ----------
# Web Pages


@app.context_processor
def add_url_to_context():
    return {"url": request.url}


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(APP_PATH, "favicon.ico")


@app.route("/")
def home():
    """Home page"""
    # logger.debug('app.config = {}'.format(app.config))
    date, version = git_version()
    return render_template("home.html", git_date=date, git_version=version)


@app.route("/jobs", defaults={"jobname": ""})
@app.route("/jobs/", defaults={"jobname": ""})
@app.route("/jobs/<jobname>")
# @login_required
def job_list(jobname):
    """Job list page"""
    logger.info(jobname)
    return render_template("job_list.html", jobname=jobname)


@app.route("/job_execute", defaults={"jobname": ""})
@app.route("/job_execute/", defaults={"jobname": ""})
@app.route("/job_execute/<jobname>")
# @login_required
def job_execute(jobname):
    """Job execution page"""
    logger.info(jobname)
    return render_template("job_execute.html", jobname=jobname)


@app.route("/job_edit/<jobname>/<jobid>")
# @login_required
def job_edit(jobname, jobid):
    """Job edit page"""
    logger.info(jobname + " " + jobid)
    return render_template("job_edit.html", jobname=jobname, jobid=jobid)


@app.route("/job_form/<jobname>")
# @login_required
def job_form(jobname):
    """Job edit page"""
    logger.info(jobname)
    return render_template(
        "job_form.html",
        jobname=jobname,
        init_params=json.dumps(request.args.to_dict(flat=False)),
    )


@app.route("/job_definition", methods=["GET", "POST"], defaults={"jobname": ""})
@app.route("/job_definition/", methods=["GET", "POST"], defaults={"jobname": ""})
@app.route("/job_definition/<path:jobname>", methods=["GET"])
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
    if current_user.is_authenticated and current_user.has_role("admin"):
        is_admin = True
    return render_template("job_definition.html", jobname=jobname, is_admin=is_admin)


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


@app.route("/proxy/<path:uri>", methods=["GET", "POST", "DELETE"])
def proxy(uri):
    response = uws_server_request(
        "/" + uri, method=request.method, init_request=request
    )
    # logger.debug(response.headers.__dict__)
    # def generate():
    #     for chunk in r.iter_content(CHUNK_SIZE):
    #         yield chunk
    # return Response(stream_with_context(generate()), content_type = r.headers['content-type'])
    headers = {}
    for k in ["content-length", "content-disposition"]:  # , 'content-encoding']:
        if k in response.headers.__dict__["_store"]:
            headers[k] = response.headers[k]
    return Response(
        response,
        status=response.status_code,
        content_type=response.headers.get("content-type", None),
        headers=headers,
    )


def save_oidc_token(user, idp, token):
    """Keep the OpenID Connect tokens of the user (to call the server with UWS_AUTH = "OIDC")"""
    row = OIDCToken.query.filter_by(user_id=user.id).first() or OIDCToken(user_id=user.id)
    row.idp = idp
    row.token = json.dumps(dict(token))
    db.session.add(row)
    db.session.commit()


def oidc_access_token(user):
    """Valid access token of the user (refreshed if needed), or None"""
    row = OIDCToken.query.filter_by(user_id=user.id).first()
    if not row or row.idp not in idp_names:
        return None
    token = json.loads(row.token)
    if token.get("expires_at", 0) - 30 < datetime.datetime.now().timestamp():
        if not token.get("refresh_token"):
            return None
        try:
            new_token = dict(oauth._clients[row.idp].fetch_access_token(
                grant_type="refresh_token", refresh_token=token["refresh_token"]
            ))
        except Exception as e:
            logger.warning(f"Cannot refresh the OIDC access token of {user.email}: {type(e).__name__}")
            return None
        new_token.setdefault("refresh_token", token["refresh_token"])
        if token.get("id_token"):
            new_token.setdefault("id_token", token["id_token"])  # kept for the logout (id_token_hint)
        save_oidc_token(user, row.idp, new_token)
        logger.debug(f"OIDC access token of {user.email} refreshed")
        token = new_token
    return token.get("access_token")


def server_auth():
    """Authentication of the requests to the server: (auth, headers)

    UWS_AUTH = "Basic": name and OPUS token of the user (HTTP Basic).
    UWS_AUTH = "OIDC": for a user signed in with an Identity Provider, its access token
    (Bearer) and its OPUS token (X-Opus-Token), else as for Basic.
    """
    if app.config["UWS_AUTH"] not in ("Basic", "OIDC"):
        return None, {}
    if not current_user.is_authenticated:
        return HTTPBasicAuth("anonymous", "anonymous"), {}
    if app.config["UWS_AUTH"] == "OIDC":
        access_token = oidc_access_token(current_user)
        if access_token:
            return None, {"Authorization": f"Bearer {access_token}", "X-Opus-Token": current_user.token}
    return HTTPBasicAuth(current_user.email, current_user.token), {}


def uws_server_request(uri, method="GET", init_request=None):
    server_url = app.config["UWS_SERVER_URL"]
    # Remove server_url from uri if present (uri is expected to be a relative path)
    uri = uri.replace(server_url, "")
    # Add auth information (Basic, or OIDC access token + OPUS token)
    auth, headers = server_auth()
    auth_type = "OIDC" if "Authorization" in headers else ("Basic" if auth else "none")
    # Send request
    if method == "DELETE":
        response = requests.delete(f"{server_url}{uri}", auth=auth, headers=headers)
    elif method == "POST":
        post = {}
        if init_request:
            for key in list(init_request.form.keys()):
                value = init_request.form.getlist(key)
                secret = any(w in key.lower() for w in ("token", "password", "secret"))
                logger.debug(f"POST {key}: {'***' if secret else value}")
                if len(value) == 1:
                    post[key] = value[0]
                else:
                    post[key] = value
        files = {}
        if init_request:
            for fname in list(init_request.files.keys()):
                logger.debug("file: " + fname)
                fp = init_request.files[fname]
                files[fname] = (fp.filename, fp.stream, fp.content_type, fp.headers)
        response = requests.post(
            f"{server_url}{uri}", data=post, files=files, auth=auth, headers=headers
        )
    else:
        params = {}
        if init_request:
            params = init_request.args
        logger.debug(f"{method} {server_url}{uri} {params} ({auth_type})")
        response = requests.get(f"{server_url}{uri}", params=params, auth=auth, headers=headers)
    # Return response
    logger.debug(f"{method} {server_url}{uri} ({response.status_code}, {auth_type})")
    return response


# ----------
# run server


if __name__ == "__main__":
    # Run local web server
    # run(app, host='localhost', port=8080, debug=False, reloader=True)
    app.run(host="localhost", port=8080, debug=True)
    pass
