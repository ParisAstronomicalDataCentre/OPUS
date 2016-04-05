#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
"""

import traceback
import uuid
import collections
from subprocess import CalledProcessError

from bottle import Bottle, request, response, abort, redirect, run, static_file, parse_auth, view, jinja2_view
from beaker.middleware import SessionMiddleware
# from cork import Cork

from uws_classes import *
from uws_client.uws_client import session_opts, app as client_app


# Create a new application
app = Bottle()


# ----------
# Set user


def set_user():
    """Set user from request header"""
    # logger.debug(str(request.environ))
    user_name = 'anonymous'
    user_pid = 'anonymous'
    # Set user from GET
    if 'user' in request.GET:
        user_name = request.GET['user']
        if 'user_pid' in request.GET:
            user_pid = request.GET['user_pid']
        else:
            user_pid = request.GET['user']
        logger.debug('user information from GET ({}:{})'.format(user_name, user_pid))
    # Set user from REMOTE_USER if not empty
    remote_user = request.environ.get('REMOTE_USER', '')
    if remote_user:
        user_name = remote_user
        user_pid = remote_user
        logger.debug('REMOTE_USER is set: {}'.format(user_name))
    # Use Basic access authentication
    auth = request.headers.get('Authorization')
    # Using WSGI, the header is changed to HTTP_AUTHORIZATION
    # TODO: add WSGIPassAuthorization On to Apache config on voparis-uws-test
    if not auth:
        auth = request.headers.get('HTTP_AUTHORIZATION')
    if auth:
        user_name, user_pid = parse_auth(auth)
        logger.debug('Authorization: {} ({}:{})'.format(auth, user_name, user_pid))
    user = User(user_name, user_pid)
    return user


def is_job_server(ip):
    """Test if request comes from a job server"""
    # IP or part of an IP has to be in the JOB_SERVERS list
    if any(x in ip for x in JOB_SERVERS):
        return True
    else:
        logger.warning('{} wants to access {}'.format(ip, request.urlparts.path))
        return False


def is_localhost():
    """Test if localhost"""
    ip = request.environ.get('REMOTE_ADDR', '')
    if ip == '127.0.0.1':
        return True
    else:
        return False


# ----------
# Abort functions


def abort_403():
    """HTTP Error 403

    Returns:
        403 Forbidden
    """
    abort(403, 'You don\'t have permission to access {} on this server.'.format(request.urlparts.path))


def abort_404(msg=None):
    """HTTP Error 404

    Returns:
        404 Not Found
        404 Not Found + message
    """
    if msg:
        logger.warning(msg)
        abort(404, msg)
    else:
        logger.warning('404 Not Found')
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


def abort_500_except(msg=None):
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
        abort(500, 'Internal Server Error')


# ----------
# Helper functions


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root='{}/uws_server'.format(APP_PATH))


# TODO: WADL should be one of the proposed JDL
@app.get('/get_wadl/<jobname:path>')
def get_wadl(jobname):
    """Get WADL file for jobname"""
    fname = '{}/{}.wadl'.format(JDL_PATH, jobname)
    if os.path.isfile(fname):
        with open(fname) as f:
            wadl = f.readlines()
        response.content_type = 'text/xml; charset=UTF-8'
        return wadl
    abort_404('No WADL file found for ' + jobname)


@app.get('/get_jdl_json/<jobname:path>')
def get_jdl_json(jobname):
    """Get json dictionary WADL file for jobname"""
    try:
        job_def = uws_jdl.read_jdl(jobname)
        return job_def
    except UserWarning as e:
        abort_404(e.message)


@app.get('/get_script/<jobname:path>')
def get_script(jobname):
    fname = '{}/{}.sh'.format(SCRIPT_PATH, jobname)
    logger.info('Job script read: {}'.format(fname))
    if os.path.isfile(fname):
        response.content_type = 'text/plain; charset=UTF-8'
        return static_file(fname, root='/')
    abort_404('No script file found for ' + jobname)


# ----------
# Database testing


@app.route('/db/init')
def init_db():
    """Initialize the database structure with test data

    Returns:
        303 See other (on success)
        403 Forbidden (if not super_user)
        500 Internal Server Error
    """
    # user = set_user()
    #if not is_localhost():
    #    abort_403()
    try:
        filename = 'data/db_def/job_database.sqlite'
        with open(filename) as f:
            sql = f.read()
        db = storage.__dict__[STORAGE]()
        db.cursor.executescript(sql)
        db.conn.commit()
        logger.info('Database initialized using ' + filename)
    except:
        abort_500_except()
    redirect('/db/show', 303)


@app.route('/db/test')
def test_db():
    """Initialize the database structure with test data

    Returns:
        303 See other (on success)
        403 Forbidden (if not super_user)
        500 Internal Server Error
    """
    # user = set_user()
    #if not is_localhost():
    #    abort_403()
    try:
        filename = 'data/db_def/job_database_test.sqlite'
        with open(filename) as f:
            sql = f.read()
        db = storage.__dict__[STORAGE]()
        db.cursor.executescript(sql)
        db.conn.commit()
        logger.info('Database initialized using ' + filename)
    except:
        abort_500_except()
    redirect('/db/show', 303)


@app.route('/db/show')
def show_db():
    """Show database in HTML

    Returns:
        200 OK: text/html (on success)
        403 Forbidden (if not super_user)
        500 Internal Server Error (on error)
    """
    user = set_user()
    #if not is_localhost():
    #    abort_403()
    html = ''
    try:
        logger.info('Show Database for ' + user.name)
        joblist = JobList('ctbin', user)
        return joblist.to_html()
    except:
        abort_500_except()
    return html


# ----------
# Config


@app.post('/config/job_definition')
def create_new_job_definition():
    """Use filled form to create a WADL file for the given job"""
    # no need to authenticate, users can propose new jobs that will be validated
    #aaa.require(fail_redirect='/accounts/login?next=' + str(request.urlparts.path))
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
    # Create job_jdl structure
    job_def = {'description': description,
               'parameters': params,
               'results': results,
               'executionduration': execdur,
               'quote': quote}
    # Create WADL file from form
    job_jdl = uws_jdl.create_wadl(jobname, job_def)
    # Save WADL in new/
    jdl_fname = '{}/new/{}.wadl'.format(JDL_PATH, jobname)
    with open(jdl_fname, 'w') as f:
        f.write(job_jdl)
        logger.info('WADL saved: ' + jdl_fname)
    # Save bash script file in new/
    script_fname = '{}/new/{}.sh'.format(SCRIPT_PATH, jobname)
    with open(script_fname, 'w') as f:
        f.write(script.replace('\r', ''))
        logger.info('Job script save: ' + script_fname)
        # TODO: send to work cluster?
    # Back to filled form (request.headers.get('Referer')?)
    redirect('/client/job_definition?jobname=new/{}&msg=new'.format(jobname), 303)


@app.get('/config/validate_job/<jobname>')
def validate_job_definition(jobname):
    """Use filled form to create a WADL file for the given job"""
    # TODO: Restrict access to admin
    #aaa.require(role='admin', fail_redirect='/config/job_definition?jobname=new/{}&msg=restricted'.format(jobname))
    # Copy script and jdl from new
    jdl_src = '{}/new/{}.wadl'.format(JDL_PATH, jobname)
    jdl_dst = '{}/{}.wadl'.format(JDL_PATH, jobname)
    script_src = '{}/new/{}.sh'.format(SCRIPT_PATH, jobname)
    script_dst = '{}/{}.sh'.format(SCRIPT_PATH, jobname)
    # save, then copy from new/
    if os.path.isfile(jdl_src):
        if os.path.isfile(jdl_dst):
            # save file with time stamp
            mt = dt.datetime.fromtimestamp(os.path.getmtime(jdl_dst)).isoformat()
            jdl_dst_save = '{}/saved/{}_{}.wadl'.format(JDL_PATH, jobname, mt)
            os.rename(jdl_dst, jdl_dst_save)
            logger.info('Previous job WADL saved: ' + jdl_dst_save)
        shutil.copy(jdl_src, jdl_dst)
        logger.info('New job WADL copied: ' + jdl_dst)
    else:
        logger.info('No job WADL found for validation: ' + jdl_src)
        redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    if os.path.isfile(script_src):
        if os.path.isfile(script_dst):
            # save file with time stamp
            mt = dt.datetime.fromtimestamp(os.path.getmtime(script_dst)).isoformat()
            script_dst_save = '{}/saved/{}_{}.sh'.format(SCRIPT_PATH, jobname, mt)
            os.rename(script_dst, script_dst_save)
            logger.info('Previous job script saved: ' + script_dst_save)
        shutil.copy(script_src, script_dst)
        logger.info('New job script copied: ' + script_dst)
    else:
        logger.info('No job script found for validation: ' + script_src)
        redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    # Copy script to job manager
    if os.path.isfile(script_dst):
        manager = managers.__dict__[MANAGER]()
        manager.cp_script(jobname)
        logger.info('Job script copied to work cluster: ' + jobname)
    else:
        logger.info('No job script found for job: ' + jobname)
        redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    # Redirect to job_definition with message
    redirect('/client/job_definition?jobname={}&msg=validated'.format(jobname), 303)


@app.get('/config/cp_script/<jobname>')
def cp_script(jobname):
    """Use filled form to create a WADL file for the given job"""
    # TODO: Restrict access to admin
    #aaa.require(role='admin', fail_redirect='/config/job_definition?jobname={}&msg=restricted'.format(jobname))
    # Copy script to job manager
    script_dst = '{}/{}.sh'.format(SCRIPT_PATH, jobname)
    if os.path.isfile(script_dst):
        manager = managers.__dict__[MANAGER]()
        manager.cp_script(jobname)
        logger.info('Job script copied to work cluster: ' + jobname)
    else:
        logger.info('No job script found for job: ' + jobname)
        redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    # Redirect to job_definition with message
    redirect('/client/job_definition?jobname={}&msg=script_copied'.format(jobname), 303)


# ----------
# Server maintenance


@app.route('/handler/maintenance')
def maintenance():
    """Performs server maintenance, e.g. executed regularly by the server itself (localhost)

    Returns:
        200 OK: text/plain (on success)
        403 Forbidden (if not localhost)
        500 Internal Server Error (on error)
    """
    if not is_localhost():
        abort_403()
    try:
        # Get joblist
        # For each job:
        # TODO: Check consistency of dates (destruction_time > end_time > start_time > creation_time)
        # TODO: Update status if phase is not PENDING or terminal (or for all jobs?)
        # TODO: If job is SUSPENDED, try to restart the job
        # TODO: If destruction time is passed, delete job
        pass
    except:
        abort_500_except()
    # Response
    response.content_type = 'text/plain; charset=UTF-8'
    return ''


# ----------
# Interface with job queue manager


@app.post('/handler/job_event')
def job_event():
    """New events for job with given jobid_cluster

    This hook expects POST commands that must come from a referenced job server
    POST should include: jobid=, phase=, error_msg=

    Returns:
        200 OK: text/plain (on success)
        403 Forbidden (if not super_user)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    ip = request.environ.get('REMOTE_ADDR', '')
    if not is_job_server(ip):
        abort_403()
    try:
        user = set_user()
        logger.info('from {} with POST={}'.format(ip, str(request.POST.dict)))
        if 'jobid' in request.POST:
            jobid_cluster = request.POST['jobid']
            # Get job description from DB based on jobid_cluster
            job = Job('', jobid_cluster, user, get_attributes=True, from_jobid_cluster=True)
            # Update job
            if 'phase' in request.POST:
                cur_phase = job.phase
                new_phase = request.POST['phase']
                msg = ''
                if new_phase not in PHASES:
                    # TODO: remove PHASE_CONVERT, will be handled by cluster uws_oncompletion.sh
                    if new_phase in PHASE_CONVERT:
                        msg = PHASE_CONVERT[new_phase]['msg']
                        new_phase = PHASE_CONVERT[new_phase]['phase']
                    else:
                        raise UserWarning('Unknown new phase ' + new_phase + ' for job ' + job.jobid)
                # If phase=ERROR, add error message if available
                if new_phase == 'ERROR':
                    if 'error_msg' in request.POST:
                        msg = request.POST['error_msg']
                    job.change_status('ERROR', msg)
                    logger.info('{} {} ERROR reported (from {})'.format(job.jobname, job.jobid, ip))
                elif new_phase != cur_phase:
                    job.change_status(new_phase, msg)
                    logger.info('{} {} phase {} --> {} (from {})'
                                ''.format(job.jobname, job.jobid, cur_phase, new_phase, ip))
                else:
                    raise UserWarning('Phase is already ' + new_phase)
            elif 'result' in request.POST:
                # TODO: get result from job.manager
                # TODO: add result to job.results and save to storage
                pass
            else:
                raise UserWarning('Unknown event sent for job ' + job.jobid)
        else:
            raise UserWarning('jobid is not defined in POST')
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except UserWarning as e:
        abort_500(e.message)
    except:
        abort_500_except()
    # Response
    response.content_type = 'text/plain; charset=UTF-8'
    return ''


# ----------
# /<jobname>


@app.route('/rest/<jobname>')
def get_joblist(jobname):
    """Get list for <jobname> jobs

    Returns:
        the <jobs> element in the UWS schema, can be empty
        200 OK: text/xml (on success)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname)
        joblist = JobList(jobname, user)
        xml_out = joblist.to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
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
    jobid = str(uuid.uuid4())
    try:
        user = set_user()
        # TODO: Check if form submitted correctly, detect file size overflow?
        # TODO: add attributes: execution_duration, mem, nodes, ntasks-per-node
        # Set new job description from POSTed parameters
        job = Job(jobname, jobid, user, from_post=request)
        logger.info(jobname + ' ' + jobid + ' CREATED')
        # If PHASE=RUN, start job
        if request.forms.get('PHASE') == 'RUN':
            job.start()
            logger.info(jobname + ' ' + jobid + ' started with jobid_cluster=' + str(job.jobid_cluster))
    except UserWarning as e:
        abort_500(e.message)
    except CalledProcessError as e:
        abort_500_except('STDERR output:\n' + e.output)
    except:
        abort_500_except()
    # Response
    redirect('/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>


@app.route('/rest/<jobname>/<jobid>')
def get_job(jobname, jobid):
    """Get description for job <jobid>

    Returns:
        the <job> element in the UWS schema
        200 OK: text/xml (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True, get_results=True)
        # Return job description in UWS format
        xml_out = job.to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Delete job
        job.delete()
        logger.info(jobname + ' ' + jobid + ' DELETED')
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except CalledProcessError as e:
        abort_500_except('STDERR output:\n' + e.output)
    except:
        abort_500_except()
    # Response
    redirect('/rest/' + jobname, 303)


@app.post('/rest/<jobname>/<jobid>')
def post_job(jobname, jobid):
    """Alias for delete_job() if ACTION=DELETE"""
    try:
        user = set_user()
        logger.info('delete ' + jobname + ' ' + jobid)
        if request.forms.get('ACTION') == 'DELETE':
            # Get job description from DB
            job = Job(jobname, jobid, user, get_attributes=True)
            # Delete job
            job.delete()
            logger.info(jobname + ' ' + jobid + ' DELETED')
        else:
            raise UserWarning('ACTION=DELETE is not specified in POST')
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except UserWarning as e:
        abort_500(e.message)
    except CalledProcessError as e:
        abort_500_except('STDERR output:\n' + e.output)
    except:
        abort_500_except()
    redirect('/rest/' + jobname, 303)


# ----------
# /<jobname>/<jobid>/phase


@app.route('/rest/<jobname>/<jobid>/phase')
def get_phase(jobname, jobid):
    """Get the phase of job <job-id>

    Returns:
        200 OK: text/plain: one of the fixed strings (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.phase
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        if 'PHASE' in request.forms:
            new_phase = request.forms.get('PHASE')
            logger.info('PHASE=' + new_phase + ' ' + jobname + ' ' + jobid)
            if new_phase == 'RUN':
                # Get job description from DB
                job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True)
                # Check if phase is PENDING
                if job.phase not in ['PENDING']:
                    raise UserWarning('Job has to be in PENDING phase')
                # Start job
                job.start()
                logger.info(jobname + ' ' + jobid + ' STARTED with jobid_cluster=' + str(job.jobid_cluster))
            elif new_phase == 'ABORT':
                # Get job description from DB
                job = Job(jobname, jobid, user, get_attributes=True)
                # Abort job
                job.abort()
                logger.info(jobname + ' ' + jobid + ' ABORTED by user ' + user.name)
            else:
                raise UserWarning('PHASE=' + new_phase + ' not expected')
        else:
            raise UserWarning('PHASE keyword is not specified in POST')
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except UserWarning as e:
        abort_500(e.message)
    except CalledProcessError as e:
        abort_500_except('STDERR output:\n' + e.output)
    except:
        abort_500_except()
    # Response
    redirect('/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>/executionduration


@app.route('/rest/<jobname>/<jobid>/executionduration')
def get_executionduration(jobname, jobid):
    """Get the maximum execution duration of job <jobid>

    Returns:
        200 OK: text/plain: integer number of seconds (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.execution_duration)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get value from POST
        if 'EXECUTIONDURATION' not in request.forms:
            raise UserWarning('EXECUTIONDURATION keyword required')
        new_value = request.forms.get('EXECUTIONDURATION')
        # Check new value
        try:
            new_value = int(new_value)
        except ValueError:
            raise UserWarning('Execution duration must be an integer or a float')
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # TODO: check phase?

        # Change value
        job.set_attribute('execution_duration', new_value)
        logger.info(jobname + ' ' + jobid + ' set execution_duration=' + str(new_value))
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except UserWarning as e:
        abort_500(e.message)
    except:
        abort_500_except()
    # Response
    redirect('/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>/destruction


@app.route('/rest/<jobname>/<jobid>/destruction')
def get_destruction(jobname, jobid):
    """Get the destruction instant for job <jobid>

    Returns:
        200 OK: text/plain: time in ISO8601 format (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.destruction_time
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
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
                raise UserWarning('Destruction time must be in ISO8601 format ({})'.format(e.message))
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Change value
        # job.set_destruction_time(new_value)
        job.set_attribute('destruction_time', new_value)
        logger.info(jobname + ' ' + jobid + ' set destruction_time=' + new_value)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except UserWarning as e:
        abort_500(e.message)
    except:
        abort_500_except()
    # Response
    redirect('/rest/' + jobname + '/' + jobid, 303)


# ----------
# /<jobname>/<jobid>/error


@app.route('/rest/<jobname>/<jobid>/error')
def get_error(jobname, jobid):
    """Get any error message associated with job <jobid>

    Returns:
        any representation appropriate to the implementing service
        200 OK: text/plain: error message (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.error
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/quote


@app.route('/rest/<jobname>/<jobid>/quote')
def get_quote(jobname, jobid):
    """Get the Quote for job <jobid>

    Returns:
        200 OK: text/plain: integer number of seconds (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.quote)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


# ----------
# /<jobname>/<jobid>/parameters


@app.route('/rest/<jobname>/<jobid>/parameters')
def get_parameters(jobname, jobid):
    """Get parameters for job <jobid>

    Returns:
        the <parameters> element in the UWS schema
        200 OK: text/xml (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        # Return job parameters in UWS format
        xml_out = job.parameters_to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info('param=' + pname + ' ' + jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        # Check if param exists
        if pname not in job.parameters:
            raise storage.NotFoundWarning('Parameter "{}" NOT FOUND for job "{}"'.format(pname, jobid))
        # Return parameter
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.parameters[pname]['value'])
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info('pname=' + pname + ' ' + jobname + ' ' + jobid)
        # Get value from POST
        if 'VALUE' not in request.forms:
            raise UserWarning('VALUE keyword required')
        new_value = request.forms.get('VALUE')
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True)
        # TODO: Check if new_value format is correct (from WADL?)
        # Change value
        if job.phase == 'PENDING':
            job.set_parameter(pname, new_value)
            logger.info(jobname + ' ' + jobid + ' set parameter ' + pname + '=' + new_value)
        else:
            raise UserWarning('Job "{}" must be in PENDING state (currently {}) to change parameter'
                              ''.format(jobid, job.phase))
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except UserWarning as e:
        abort_500(e.message)
    except:
        abort_500_except()
    # Response
    redirect('/rest/' + jobname + '/' + jobid + '/parameters', 303)


# ----------
# /<jobname>/<jobid>/results


@app.route('/rest/<jobname>/<jobid>/results')
def get_results(jobname, jobid):
    """Get results for job <jobid>

    Returns:
        the <results> element in the UWS schema
        200 OK: text/xml (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_results=True)
        # Return job results in UWS format
        xml_out = job.results_to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info('rname=' + rname + ' ' + jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_parameters=True, get_results=True)
        # Check if result exists
        if rname not in job.results:
            raise storage.NotFoundWarning('Result "{}" NOT FOUND for job "{}"'.format(rname, jobid))
        # Return result
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.results[rname]['url'])
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


@app.route('/get_result_file/<jobid>/<rname>')
def get_result_file(jobid, rname):
    """Get result file <rname>/<rfname> for job <jobid>

    Returns:
        200 OK: file (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    user = set_user()
    # Get job description from DB
    job = Job('', jobid, user, get_parameters=True, get_results=True)
    # Check if result exists
    if rname not in job.results:
        raise storage.NotFoundWarning('Result "{}" NOT FOUND for job "{}"'.format(rname, jobid))
    # Return result
    rfname = job.get_result_filename(rname)
    #response.content_type = 'text/plain; charset=UTF-8'
    #return str(job.results[result]['url'])
    media_type = job.results[rname]['mediaType']
    logger.debug('{} {} {} {} {}'.format(job.jobname, jobid, rname, rfname, media_type))
    response.set_header('Content-type', media_type)
    if any(x in media_type for x in ['text', 'xml']):
        return static_file(rfname, root='{}/{}/results'.format(JOBDATA_PATH, job.jobid), mimetype=media_type)
    else:
        return static_file(rfname, root='{}/{}/results'.format(JOBDATA_PATH, job.jobid), mimetype=media_type, download=rfname)


# ----------
# /<jobname>/<jobid>/owner


@app.route('/rest/<jobname>/<jobid>/owner')
def get_owner(jobname, jobid):
    """Get the owner of the job <jobid>

    Returns:
        200 OK: text/plain: an appropriate identifier as discussed in 3 (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.owner
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


# ----------
# run server

# Create session
# app = SessionMiddleware(app, session_opts)

# Merge UWS Client app
if MERGE_CLIENT:
    app.merge(client_app)
    app = SessionMiddleware(app, session_opts)



if __name__ == '__main__':
    # Run local web server
    run(app, host='localhost', port=8080, debug=False, reloader=True)