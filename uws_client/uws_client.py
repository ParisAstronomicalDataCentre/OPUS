"""
Created on Wed Mar 2 2016

UWS client implementation using bottle.py

@author: mservillat
"""

import os
import logging
from bottle import Bottle, request, response, abort, redirect, run, static_file, parse_auth, TEMPLATE_PATH, view, jinja2_view
from beaker.middleware import SessionMiddleware
from cork import Cork


# Create a new application
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
aaa = Cork('uws_client/cork_conf')

# Settings
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
UWS_SERVER_URL = ''
LOG_FILE = 'logs/client.log'
TEMPLATE_PATH.insert(0, APP_PATH + '/uws_client/views/')

# Set logger
logging.basicConfig(
    filename=LOG_FILE,
    format='[%(asctime)s] %(levelname)s %(module)s.%(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ----------
# Helper functions


@app.route('/static/<path:path>')
def static(path):
    """Access to static files (css, js, ...)"""
    return static_file(path, root='{}/uws_client/static'.format(APP_PATH))


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root='{}/uws_client'.format(APP_PATH))


# ----------
# Manage user accounts


@app.route('/accounts/login')
@jinja2_view('login_form.html')
def login_form():
    """Serve login form"""
    next_page = request.query.get('next', '/')
    msg = request.query.get('msg', '')
    msg_text = {
        'failed': 'Authentication failed',
    }
    if msg in msg_text:
        return {'next': next_page, 'message': msg_text[msg]}
    return {'next': next_page}


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
    aaa.login(username, password, success_redirect=next_page, fail_redirect='/accounts/login?msg=failed')


@app.route('/accounts/logout')
def logout():
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
    aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    session = request.environ['beaker.session']
    jobname = request.query.get('jobname', '')
    return {'session': session, 'jobname': jobname}


@app.route('/client/job_edit/<jobname>/<jobid>')
@jinja2_view('job_edit.html')
def job_edit(jobname, jobid):
    """Job edit page"""
    logger.info(jobname + ' ' + jobid)
    aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    session = request.environ['beaker.session']
    return {'session': session, 'jobname': jobname, 'jobid': jobid}


@app.route('/client/job_form/<jobname>')
@jinja2_view('job_form.html')
def job_form(jobname):
    """Job edit page"""
    logger.info(jobname)
    aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    session = request.environ['beaker.session']
    return {'session': session, 'jobname': jobname}


@app.get('/client/job_definition')
@jinja2_view('job_definition.html')
def job_definition():
    """Show form for new job definition"""
    logger.info('')
    # no need to authenticate, users can propose new jobs that will be validated
    #aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
    is_admin = False
    if not aaa.user_is_anonymous:
        if aaa.current_user.role == 'admin':
            is_admin = True
    session = request.environ['beaker.session']
    jobname = request.query.get('jobname', '')
    msg = request.query.get('msg', '')
    msg_text = {
        'new': 'New job definition has been saved as {}'.format(jobname),
        'restricted': 'Access is restricted to administrators',
        'script_copied': 'Job script {}.sh has been copied to work cluster'.format(jobname),
        'validated': 'Job definition for new/{jn} has been validated and renamed {jn}'.format(jn=jobname),
        'notfound': 'Job definition for new/{jn} was not found on the server. Cannot validate.'.format(jn=jobname),
    }
    if msg in msg_text:
        return {'session': session, 'is_admin': is_admin, 'jobname': jobname, 'message': msg_text[msg]}
    return {'session': session, 'is_admin': is_admin, 'jobname': jobname}


# ----------
# run server


# Create session
client_app = SessionMiddleware(app, session_opts)

if __name__ == '__main__':
    # Run local web server
    run(client_app, host='localhost', port=8080, debug=False, reloader=True)
