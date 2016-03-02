"""
Created on Wed Mar 2 2016

UWS client implementation using bottle.py

@author: mservillat
"""


from bottle import Bottle, request, response, abort, redirect, run, static_file, parse_auth, view, jinja2_view
from beaker.middleware import SessionMiddleware
from cork import Cork


# Create a new application
app = Bottle()

# Create session
session_opts = {
    'session.cookie_expires': True,
    'session.encrypt_key': 'please use a random key and keep it secret!',
    'session.httponly': True,
    'session.timeout': 3600 * 24,  # 1 day
    'session.type': 'cookie',
    'session.validate_key': True,
}

aaa = Cork('example_conf')

# ----------
# Manage user accounts


def postd():
    return request.forms

def post_get(name, default=''):
    return request.POST.get(name, default).strip()

@app.post('/accounts/login')
def login():
    """Authenticate users"""
    username = post_get('username')
    password = post_get('password')
    aaa.login(username, password, success_redirect='/', fail_redirect='/accounts/login')

@app.route('/accounts/logout')
def logout():
    aaa.logout(success_redirect='/accounts/login')

@app.route('/accounts/admin')
@view('admin_page')
def admin():
    """Only admin users can see this"""
    aaa.require(role='admin', fail_redirect='/sorry_page')
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


@app.route('/accounts/login')
@view('login_form')
def login_form():
    """Serve login form"""
    return {}


@app.route('/sorry_page')
def sorry_page():
    """Serve sorry page"""
    return '<p>Sorry, you are not authorized to perform this action</p>'



# ----------
# Web Pages


@app.route('/')
@jinja2_view('home.html')
def home():
    """Home page"""
    return {'aaa': aaa}
    # response.content_type = 'text/html; charset=UTF-8'
    # return "UWS v1.0 server implementation<br>(c) Observatoire de Paris 2015"


@app.route('/client/job_list')
@jinja2_view('job_list.html')
def job_list():
    """Job list page"""
    logger.info('')
    jobname = request.query.get('jobname', '')
    return {'jobname': jobname}


@app.route('/client/job_edit/<jobname>/<jobid>')
@jinja2_view('job_edit.html')
def job_edit(jobname, jobid):
    """Job edit page"""
    logger.info(jobname + ' ' + jobid)
    return {'jobname': jobname, 'jobid': jobid}


@app.route('/client/job_form/<jobname>')
@jinja2_view('job_form.html')
def job_form(jobname):
    """Job edit page"""
    logger.info(jobname)
    return {'jobname': jobname}


@app.get('/config/job_definition')
@jinja2_view('job_definition.html')
def job_definition():
    """Show form for new job definition"""
    logger.info('')
    jobname = request.query.get('jobname', '')
    if request.query.get('msg', '') == 'new':
        msg = 'New job definition has been saved as {}'.format(jobname)
        return {'jobname': jobname, 'message': msg}
    return {'jobname': jobname}


@app.post('/config/job_definition')
def create_new_job_definition():
    """Use filled form to create a WADL file for the given job"""
    # Read form
    keys = request.forms.keys()
    jobname = request.forms.get('name').split('/')[-1]
    description = request.forms.get('description')
    execdur = request.forms.get('executionduration')
    quote = request.forms.get('quote')
    script = request.forms.get('script')
    params = collections.OrderedDict()
    iparam = 1
    while 'param_name_' + str(iparam) in keys:
        pname = request.forms.get('param_name_' + str(iparam))
        if pname:
            ptype = request.forms.get('param_type_' + str(iparam))
            pdefault = request.forms.get('param_default_' + str(iparam))
            preq = request.forms.get('param_required_' + str(iparam))
            pdesc = request.forms.get('param_description_' + str(iparam))
            params[pname] = {
                'type': ptype,
                'default': pdefault,
                'required': (preq == 'on'),
                'description': pdesc,
            }
        iparam += 1
    results = collections.OrderedDict()
    iresult = 1
    while 'result_name_' + str(iresult) in keys:
        rname = request.forms.get('result_name_' + str(iresult))
        if rname:
            rtype = request.forms.get('result_type_' + str(iresult))
            rdefault = request.forms.get('result_default_' + str(iresult))
            rdesc = request.forms.get('result_description_' + str(iresult))
            results[rname] = {
                'mediaType': rtype,
                'default': rdefault,
                'description': rdesc,
            }
        iresult += 1
    # Create job_wadl structure
    job_def = {'description': description,
               'parameters': params,
               'results': results,
               'executionduration': execdur,
               'quote': quote}
    # Create WADL file from form
    job_wadl = uws_jdl.create_wadl(jobname, job_def)
    # Save WADL in new/
    wadl_fname = '{}/new/{}.wadl'.format(WADL_PATH, jobname)
    with open(wadl_fname, 'w') as f:
        f.write(job_wadl)
        logger.info('WADL saved: ' + wadl_fname)
    # Save bash script file in new/
    script_fname = '{}/new/{}.sh'.format(SCRIPT_PATH, jobname)
    with open(script_fname, 'w') as f:
        f.write(script.replace('\r', ''))
        logger.info('Job script save: ' + script_fname)
        # TODO: send to work cluster?
    # Back to filled form
    redirect('/config/job_definition?jobname=new/{}&msg=new'.format(jobname), 303)


# ----------
# run server

app = SessionMiddleware(app, session_opts)

if __name__ == '__main__':
    # Run local web server
    run(app, host='localhost', port=8080, debug=False, reloader=True)
