#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
"""

import traceback
import glob
import re
import uuid
import collections
import threading
from subprocess import CalledProcessError

from bottle import Bottle, request, response, abort, redirect, run, static_file
from beaker.middleware import SessionMiddleware
# from cork import Cork

from uws_classes import *


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

def set_user():
    global logger
    """Set user from request header"""
    # Use anonymous as default
    user_name = 'anonymous'
    user_pid = 'anonymous'
    # Check if REMOTE_USER is set by web server or use Basic Auth from header
    if request.auth:
        user_name, user_pid = request.auth
        if not user_pid:
            user_pid = 'remote_user'
        # logger.debug('{}:{}'.format(user_name, user_pid))
    # # Set user from GET
    # if 'user' in request.GET:
    #     user_name = request.GET['user']
    #     if 'user_pid' in request.GET:
    #         user_pid = request.GET['user_pid']
    #     else:
    #         user_pid = request.GET['user']
    #     logger.debug('user information from GET ({}:{})'.format(user_name, user_pid))
    # # Set user from REMOTE_USER if not empty
    # remote_user = request.environ.get('REMOTE_USER', '')
    # if remote_user:
    #     user_name = remote_user
    #     user_pid = remote_user
    #     logger.debug('REMOTE_USER is set: {}'.format(user_name))
    # # Use Basic access authentication
    # auth = request.headers.get('Authorization')
    # Using WSGI, the header is changed to HTTP_AUTHORIZATION
    # if not auth:
    #     auth = request.headers.get('HTTP_AUTHORIZATION')
    # if auth:
    #     logger.debug('Authorization: {}'.format(auth))
    #     user_name, user_pid = parse_auth(auth)
    #     logger.debug('Authorization: {}:{}'.format(user_name, user_pid))
    # Create user object
    user = User(user_name, user_pid)
    # Add user name at the end of each log entry
    #logger = CustomAdapter(logger_init, {'username': user_name})
    return user


def is_job_server(ip):
    """Test if request comes from a job server"""
    # IP or part of an IP has to be in the JOB_SERVERS list
    matching = [x for x in JOB_SERVERS if x in ip]
    if matching:
        logger.info('{} from {} ({})'.format(request.urlparts.path, ip, JOB_SERVERS[matching[0]]))
        return True
    else:
        logger.warning('{} wants to access {}'.format(ip, request.urlparts.path))
        return False


def is_client_trusted(ip):
    """Test if request comes from a job server"""
    # IP or part of an IP has to be in the TRUSTED_CLIENTS list
    # TODO: ip here is the ip of the web browser (request sent from javascript...) should trust the client URL maybe?
    # TODO: or access those pages from web server, not web browser
    matching = [x for x in TRUSTED_CLIENTS if x in ip]
    if matching:
        logger.info('{} from {} ({})'.format(request.urlparts.path, ip, TRUSTED_CLIENTS[matching[0]]))
        return True
    else:
        logger.warning('{} wants to access {}'.format(ip, request.urlparts.path))
        return False


def is_localhost():
    """Test if localhost"""
    ip = request.environ.get('REMOTE_ADDR', '')
    logger.debug(ip)
    if ip == BASE_IP:
        return True
    else:
        return False


# ----------
# Abort functions
# ----------


def abort_403(msg=''):
    """HTTP Error 403

    Returns:
        403 Forbidden
    """
    logger.warning('403 Forbidden: {} ({})'.format(msg, request.urlparts.path))
    abort(403, 'You don\'t have permission to access {} on this server. \n{}'
               ''.format(request.urlparts.path, msg))


def abort_404(msg=None):
    """HTTP Error 404

    Returns:
        404 Not Found
        404 Not Found + message
    """
    if msg:
        logger.warning('404 Not Found: {} ({})'.format(msg, request.urlparts.path))
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
# ----------


@app.route('/')
def home():
    redirect('/client')
    # return 'OPUS'


@app.route('/favicon.ico')
def favicon():
    return static_file('favicon.ico', root=APP_PATH)


@app.get('/get_jdl/<jobname:path>')
def get_jdl(jobname):
    """
    Get JDL file for jobname
    :param jobname:
    :return: WADL file
    """
    #logger.info(jobname)
    fname = '{}/votable/{}_vot.xml'.format(JDL_PATH, jobname)
    #logger.info(fname)
    if os.path.isfile(fname):
        with open(fname) as f:
            jdl = f.readlines()
        response.content_type = 'text/xml; charset=UTF-8'
        return jdl
    abort_404('No WADL file found for ' + jobname)


@app.get('/get_jdl_json/<jobname:path>')
def get_jdl_json(jobname):
    """
    Get json description file for jobname
    :param jobname:
    :return: json description
    """
    try:
        #logger.info(jobname)
        jdl = uws_jdl.__dict__[JDL]()
        jdl.read(jobname)
        return jdl.content
    except UserWarning as e:
        abort_404(e.message)


@app.get('/get_script/<jobname:path>')
def get_script(jobname):
    """
    Get script file as text
    :param jobname:
    :return:
    """
    fname = '{}/{}.sh'.format(SCRIPT_PATH, jobname)
    logger.info('Job script read: {}'.format(fname))
    if os.path.isfile(fname):
        response.content_type = 'text/plain; charset=UTF-8'
        return static_file(fname, root='/')
    abort_404('No script file found for ' + jobname)


@app.get('/get_jobnames')
def get_jobnames():
    """
    Get list of available jobs on server
    :return: list of job names in json
    """
    try:
        # jobnames = ['copy', 'ctbin']
        # List jdl files (=available jobs)
        flist = glob.glob('{}/*.sh'.format(SCRIPT_PATH))
        # Check if JDL file exists on server?
        jobnames = {'jobnames': [os.path.splitext(os.path.basename(f))[0] for f in flist]}
        return jobnames
    except UserWarning as e:
        abort_404(e.message)


@app.get('/get_prov/<jobname>/<jobid>')
def get_prov(jobname, jobid):
    """
    Get list of available jobs on server
    :return: list of job names in json
    """
    try:
        user = set_user()
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True, get_results=True, check_user=False)
        # Get JDL
        job.jdl.read(jobname)
        # Return job provenance
        pdoc = voprov.job2prov(job)
        dot = voprov.prov2dot(pdoc)
        svg_content = dot.create(format="svg")
        response.content_type = 'text/xml; charset=UTF-8'
        return svg_content
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


# ----------
# Database testing
# ----------


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
        filename = APP_PATH + '/uws_server/job_database.sqlite'
        with open(filename) as f:
            sql = f.read()
        db = storage.__dict__[STORAGE + 'JobStorage']()
        db.cursor.executescript(sql)
        db.conn.commit()
        logger.info('Database initialized using ' + filename)
    except:
        abort_500_except()
    redirect('/db/show/dummy', 303)


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
        filename = APP_PATH + '/uws_server/job_database_test.sqlite'
        with open(filename) as f:
            sql = f.read()
        db = storage.__dict__[STORAGE + 'JobStorage']()
        db.cursor.executescript(sql)
        db.conn.commit()
        logger.info('Database initialized using ' + filename)
    except:
        abort_500_except()
    redirect('/db/show/dummy', 303)


@app.route('/db/show/<jobname>')
def show_db(jobname):
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
        joblist = JobList(jobname, user)
        return joblist.to_html()
    except:
        abort_500_except()
    return html


# ----------
# Config
# ----------


@app.post('/config/job_definition')
def create_new_job_definition():
    """Use posted parameters to create a new JDL file for the given job"""
    # No need to authenticate, users can propose new jobs that will have to be validated
    # Check if client is trusted? not really needed
    jobname = ''
    ip = request.environ.get('REMOTE_ADDR', '')
    if not is_client_trusted(ip):
        abort_403()
    try:
        jobname = request.forms.get('name').split('/')[-1]
        # Create JDL file from job_jdl
        jdl = uws_jdl.__dict__[JDL]()
        jdl.set_from_post(request.forms)
        # Save as a new job description
        jdl.save('new/' + jobname)
        # Save bash script file in new/
        jdl.save_script('new/' + jobname, request.forms.get('script'))
    except:
        abort_500_except()
    # Response
    response.content_type = 'text/plain; charset=UTF-8'
    return 'New job created: new/{}'.format(jobname)
    # redirect('/client/job_definition?jobname=new/{}&msg=new'.format(jobname), 303)


@app.get('/config/validate_job/<jobname>')
def validate_job_definition(jobname):
    """Use filled form to create a JDL file for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    ip = request.environ.get('REMOTE_ADDR', '')
    if not is_client_trusted(ip):
        abort_403()
    try:
        # Copy script and jdl from new
        jdl = uws_jdl.__dict__[JDL]()
        jdl_src = '{}/new/{}{}'.format(jdl.jdl_path, jobname, jdl.extension)
        jdl_dst = '{}/{}{}'.format(jdl.jdl_path, jobname, jdl.extension)
        script_src = '{}/new/{}.sh'.format(jdl.script_path, jobname)
        script_dst = '{}/{}.sh'.format(jdl.script_path, jobname)
        # Save, then copy from new/
        if os.path.isfile(jdl_src):
            if os.path.isfile(jdl_dst):
                # Save file with time stamp
                mt = dt.datetime.fromtimestamp(os.path.getmtime(jdl_dst)).isoformat()
                jdl_dst_save = '{}/saved/{}_{}{}'.format(jdl.jdl_path, jobname, mt, jdl.extension)
                os.rename(jdl_dst, jdl_dst_save)
                logger.info('Previous job JDL saved: ' + jdl_dst_save)
            shutil.copy(jdl_src, jdl_dst)
            logger.info('New job JDL copied: ' + jdl_dst)
        else:
            logger.info('No job JDL found for validation: ' + jdl_src)
            abort_500('No job JDL found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
        if os.path.isfile(script_src):
            if os.path.isfile(script_dst):
                # Save file with time stamp
                mt = dt.datetime.fromtimestamp(os.path.getmtime(script_dst)).isoformat()
                script_dst_save = '{}/saved/{}_{}.sh'.format(SCRIPT_PATH, jobname, mt)
                os.rename(script_dst, script_dst_save)
                logger.info('Previous job script saved: ' + script_dst_save)
            shutil.copy(script_src, script_dst)
            logger.info('Job script copied: ' + script_dst)
            # Copy script to job manager
            manager = managers.__dict__[MANAGER + 'Manager']()
            manager.cp_script(jobname)
            logger.info('Job script copied to work cluster: ' + jobname)
        else:
            logger.info('No job script found for validation: ' + script_src)
            abort_500('No job script found for ' + jobname)
            # redirect('/client/job_definition?jobname={}&msg=notfound'.format(jobname), 303)
    except:
        abort_500_except()
    # Return code 200
    response.content_type = 'text/plain; charset=UTF-8'
    return 'Job {} validated'.format(jobname)
    # redirect('/client/job_definition?jobname={}&msg=validated'.format(jobname), 303)


@app.get('/config/cp_script/<jobname>')
def cp_script(jobname):
    """copy script to job manager for the given job"""
    # Check if client is trusted (only admin should be allowed to validate a job)
    ip = request.environ.get('REMOTE_ADDR', '')
    if not is_client_trusted(ip):
        abort_403()
    try:
        # Copy script to job manager
        script_dst = '{}/{}.sh'.format(SCRIPT_PATH, jobname)
        if os.path.isfile(script_dst):
            manager = managers.__dict__[MANAGER + 'Manager']()
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


# ----------
# Server maintenance
# ----------


@app.route('/handler/maintenance/<jobname>')
def maintenance(jobname):
    """Performs server maintenance, e.g. executed regularly by the server itself (localhost)

    Returns:
        200 OK: text/plain (on success)
        403 Forbidden (if not localhost)
        500 Internal Server Error (on error)
    """
    global logger
    if not is_localhost():
        abort_403()
    try:
        user = User('maintenance', 'maintenance')
        logger = logger_init
        logger.info('Maintenance checks for {}'.format(jobname))
        # Get joblist
        joblist = JobList(jobname, user, check_user=False)
        for j in joblist.jobs:
            # For each job:
            now = dt.datetime.now()
            job = Job(jobname, j['jobid'], user,
                      get_attributes=True, get_parameters=False, get_results=False,
                      check_user=False)
            # TODO: Check consistency of dates (destruction_time > end_time > start_time > creation_time)
            if not job.start_time and job.phase not in ['PENDING', 'QUEUED']:
                logger.warning('Start time not set for {} {}'.format(jobname, job.jobid))
            # TODO: Update status if phase is not PENDING or terminal (or for all jobs?)
            if job.phase in ['QUEUED', 'EXECUTING', 'UNKNOWN']:
                phase = job.phase
                new_phase = job.get_status()  # will update the phase from manager
                if new_phase != phase:
                    logger.warning('Status has changed for {} {}: {} --> {}'
                                   ''.format(jobname, job.jobid, phase, new_phase))
            # TODO: If job is SUSPENDED, try to restart the job -> done by manager?
            # TODO: If destruction time is passed, delete or archive job
            destruction_time = dt.datetime.strptime(job.destruction_time, DT_FMT)
            if destruction_time < now:
                logger.warning('Job should be deleted/archived: {} {}'.format(jobname, job.jobid))
        pass
    except JobAccessDenied as e:
        abort_403(e.message)
    except:
        abort_500_except()
    # Response
    response.content_type = 'text/plain; charset=UTF-8'
    return 'Maintenance performed\n'


# ----------
# Interface with job queue manager
# ----------


@app.post('/handler/job_event')
def job_event():
    """New events for job with given pid

    This hook expects POST commands that must come from a referenced job server
    POST should include: jobid=, phase=, error_msg=

    Returns:
        200 OK: text/plain (on success)
        403 Forbidden (if not super_user)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    global logger
    ip = request.environ.get('REMOTE_ADDR', '')
    if not is_job_server(ip):
        abort_403()
    try:
        user = User('job_event', 'job_event')
        logger = logger_init
        logger.info('from {} with POST={}'.format(ip, str(request.POST.dict)))
        if 'jobid' in request.POST:
            pid = request.POST['jobid']
            # Get job properties from DB based on pid
            job = Job('', pid, user, get_attributes=True, from_pid=True, check_user=False)
            # Update job
            if 'phase' in request.POST:
                cur_phase = job.phase
                new_phase = request.POST['phase']
                msg = ''
                if new_phase not in PHASES:
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
                    logger.info('ERROR reported for job {} {} (from {})'.format(job.jobname, job.jobid, ip))
                elif new_phase != cur_phase:
                    job.change_status(new_phase, msg)
                    logger.info('Phase {} --> {} for job {} {} (from {})'
                                ''.format(cur_phase, new_phase, job.jobname, job.jobid, ip))
                else:
                    raise UserWarning('Phase is already ' + new_phase)
            else:
                raise UserWarning('Unknown event sent for job ' + job.jobid)
        else:
            raise UserWarning('jobid is not defined in POST')
    except JobAccessDenied as e:
        abort_403(e.message)
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
# ----------


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
        logger.info('{} [{}]'.format(jobname, user))
        # UWS v1.1 PHASE keyword
        phase = None
        if 'PHASE' in request.query:
            # Allow for multiple PHASE keywords to be sent
            phase = re.split('&?PHASE=', request.query_string)[1:]

        # TODO: UWS v1.1 AFTER keyword
        # TODO: UWS v1.1 LAST keyword
        joblist = JobList(jobname, user, phase=phase)
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
        logger.info('{} {} CREATED [{}]'.format(jobname, jobid, user))
        # If PHASE=RUN, start job
        if request.forms.get('PHASE') == 'RUN':
            job.start()
            logger.info('{} {} started with pid={} [{}]'
                        ''.format(jobname, jobid, str(job.pid), user))
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
    try:
        user = set_user()
        # logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user,
                  get_attributes=True, get_parameters=True, get_results=True,
                  check_user=False)
        # UWS v1.1 blocking behaviour
        if job.phase in ACTIVE_PHASES:
            client_phase = request.query.get('PHASE', job.phase)
            wait_time = int(request.query.get('WAIT', False))
            if (client_phase == job.phase) and (wait_time > 0):
                change_status_signal = signal('job_status')
                change_status_event = threading.Event()

                def receiver(sender, **kw):
                    logger.info('{}: {} is now {} [{}]'.format(sender, kw.get('sig_jobid'), kw.get('sig_phase'), user))
                    # Set event if job changed
                    if (kw.get('sig_jobid') == jobid) and (kw.get('sig_phase') != job.phase):
                        change_status_event.set()
                        return '{}: signal received and job updated'.format(jobid)
                    return '{}: signal received but job not concerned'.format(jobid)

                # Connect to signal
                change_status_signal.connect(receiver)
                # Wait for signal event
                logger.info('{}: Blocking for {} seconds [{}]'.format(jobid, wait_time, user))
                event_is_set = change_status_event.wait(wait_time)
                logger.info('{}: Continue execution [{}]'.format(jobid, user))
                change_status_signal.disconnect(receiver)
                # Reload job if necessary
                if event_is_set:
                    job = Job(jobname, jobid, user,
                              get_attributes=True, get_parameters=True, get_results=True,
                              check_user=False)
        # Return job description in UWS format
        xml_out = job.to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(e.message)
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
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Delete job
        job.delete()
        logger.info('{} {} DELETED [{}]'.format(jobname, jobid, user))
    except JobAccessDenied as e:
        abort_403(e.message)
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
        logger.info('deleting {} {} [{}]'.format(jobname, jobid, user))
        if request.forms.get('ACTION') == 'DELETE':
            # Get job properties from DB
            job = Job(jobname, jobid, user, get_attributes=True)
            # Delete job
            job.delete()
            logger.info('{} {} DELETED [{}]'.format(jobname, jobid, user))
        else:
            raise UserWarning('ACTION=DELETE is not specified in POST')
    except JobAccessDenied as e:
        abort_403(e.message)
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
# ----------


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
        # logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, check_user=False)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.phase
    except JobAccessDenied as e:
        abort_403(e.message)
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
            logger.info('PHASE={} {} {} [{}]'.format(new_phase, jobname, jobid, user))
            if new_phase == 'RUN':
                # Get job properties from DB
                job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True)
                # Check if phase is PENDING
                if job.phase not in ['PENDING']:
                    raise UserWarning('Job has to be in PENDING phase')
                # Start job
                job.start()
                logger.info('{} {} STARTED with pid={} [{}]'
                            ''.format(jobname, jobid, str(job.pid), user))
            elif new_phase == 'ABORT':
                # Get job properties from DB
                job = Job(jobname, jobid, user, get_attributes=True)
                # Abort job
                job.abort()
                logger.info('{} {} ABORTED [{}]'.format(jobname, jobid, user))
            else:
                raise UserWarning('PHASE=' + new_phase + ' not expected')
        else:
            raise UserWarning('PHASE keyword is not specified in POST')
    except JobAccessDenied as e:
        abort_403(e.message)
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
# ----------


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
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, check_user=False)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.execution_duration)
    except JobAccessDenied as e:
        abort_403(e.message)
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
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
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
        job = Job(jobname, jobid, user, get_attributes=True)
        # TODO: check phase?

        # Change value
        job.set_attribute('execution_duration', new_value)
        logger.info('{} {} set execution_duration= [{}]'.format(jobname, jobid, str(new_value), user))
    except JobAccessDenied as e:
        abort_403(e.message)
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
# ----------


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
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, check_user=False)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.destruction_time
    except JobAccessDenied as e:
        abort_403(e.message)
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
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
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
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True)
        # Change value
        # job.set_destruction_time(new_value)
        job.set_attribute('destruction_time', new_value)
        logger.info('{} {} set destruction_time={} [{}]'.format(jobname, jobid, new_value, user))
    except JobAccessDenied as e:
        abort_403(e.message)
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
    try:
        user = set_user()
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, check_user=False)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.error
    except JobAccessDenied as e:
        abort_403(e.message)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, check_user=False)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.quote)
    except JobAccessDenied as e:
        abort_403(e.message)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True, check_user=False)
        # Return job parameters in UWS format
        xml_out = job.parameters_to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(e.message)
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
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_parameters=True, check_user=False)
        # Check if param exists
        if pname not in job.parameters:
            raise storage.NotFoundWarning('Parameter "{}" NOT FOUND for job "{}"'.format(pname, jobid))
        # Return parameter
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.parameters[pname]['value'])
    except JobAccessDenied as e:
        abort_403(e.message)
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
        logger.info('pname={} {} {} [{}]'.format(pname, jobname, jobid, user))
        # Get value from POST
        if 'VALUE' not in request.forms:
            raise UserWarning('VALUE keyword required')
        new_value = request.forms.get('VALUE')
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True)
        # TODO: Check if new_value format is correct (from JDL?)
        # Change value
        if job.phase == 'PENDING':
            job.set_parameter(pname, new_value)
            logger.info('{} {} set parameter {}={} [{}]'.format(jobname, jobid, pname, new_value, user))
        else:
            raise UserWarning('Job "{}" must be in PENDING state (currently {}) to change parameter'
                              ''.format(jobid, job.phase))
    except JobAccessDenied as e:
        abort_403(e.message)
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
    try:
        user = set_user()
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_results=True, check_user=False)
        # Return job results in UWS format
        xml_out = job.results_to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except JobAccessDenied as e:
        abort_403(e.message)
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
        logger.info('rname={} {} {} [{}]'.format(rname, jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_results=True, check_user=False)
        # Check if result exists
        if rname not in job.results:
            raise storage.NotFoundWarning('Result "{}" NOT FOUND for job "{}"'.format(rname, jobid))
        # Return result
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.results[rname]['url'])
    except JobAccessDenied as e:
        abort_403(e.message)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


@app.route('/get_result_file/<jobid>/<rname>')  # /<rfname>')
def get_result_file(jobid, rname):  # , rfname):
    """Get result file <rname> for job <jobid>

    Returns:
        200 OK: file (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        # Get job properties from DB
        job = Job('', jobid, user, get_attributes=True, get_parameters=True, get_results=True, check_user=False)
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
        #response.content_type = 'text/plain; charset=UTF-8'
        #return str(job.results[result]['url'])
        content_type = job.results[rname]['content_type']
        logger.debug('{} {} {} {} {} [{}]'.format(job.jobname, jobid, rname, rfname, content_type, user))
        response.set_header('Content-type', content_type)
        if any(x in content_type for x in ['text', 'xml', 'json', 'image']):
            return static_file(rfname, root='{}/{}/results'.format(JOBDATA_PATH, job.jobid),
                               mimetype=content_type)
        else:
            return static_file(rfname, root='{}/{}/results'.format(JOBDATA_PATH, job.jobid),
                               mimetype=content_type, download=rfname)
    except JobAccessDenied as e:
        abort_403(e.message)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
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
    try:
        user = set_user()
        logger.info('{} {} [{}]'.format(jobname, jobid, user))
        # Get job properties from DB
        job = Job(jobname, jobid, user, get_attributes=True, check_user=False)
        # Return value
        response.content_type = 'text/plain; charset=UTF-8'
        return job.owner
    except JobAccessDenied as e:
        abort_403(e.message)
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


# ----------
# run server
# ----------


# Merge UWS Client app
if MERGE_CLIENT:
    from uws_client.uws_client_bottle import session_opts, app as client_app
    app.merge(client_app)
    app = SessionMiddleware(app, session_opts)


if __name__ == '__main__':
    # Run local web server
    run(app, host='localhost', port=8080, debug=False, reloader=True)
