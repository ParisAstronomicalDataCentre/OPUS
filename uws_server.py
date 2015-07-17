#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 2015

UWS v1.0 server implementation using bottle.py
See http://www.ivoa.net/documents/UWS/20101010/REC-UWS-1.0-20101010.html

@author: mservillat
"""

import traceback
import uuid
from subprocess import CalledProcessError
from bottle import Bottle, request, response, abort, redirect, run
from uws_classes import *

# Create a new application
app = Bottle()


# ----------
# Set user


# Send user/pwd in GET?
# REMOTE_USER set?
# COOKIE set for Shibboleth auth in service? then redirect to institution


def set_user():
    """Set user from request header"""
    user = 'anonymous'
    # Set user from REMOTE_USER if not empty
    remote_user = request.environ.get('REMOTE_USER', '')
    if remote_user:
        user = remote_user
    if 'user' in request.GET:
        user = request.GET['user']
    return user


def is_job_server(ip):
    """Test if request comes from a job server"""
    if ip in JOB_SERVERS:
        return True
    else:
        logger.info('{} wants to access {}'.format(ip, request.urlparts.path))
        return False


def is_localhost():
    """Test if localhost"""
    ip = request.environ.get('REMOTE_ADDR', '')
    if ip == '127.0.0.1':
        return True
    else:
        return False


# ----------
# Helper functions


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
# HOME


@app.route('/')
def home():
    """Home page"""
    response.content_type = 'text/html; charset=UTF-8'
    return "UWS v1.0 server implementation<br>(c) Observatoire de Paris 2015"


@app.route('/favicon.ico')
def favicon():
    """/favicon.ico not provided"""
    abort(404)


# ----------
# Database


@app.route('/init_db')
def init_db():
    """Initialize the database structure with test data

    Returns:
        303 See other (on success)
        403 Forbidden (if not super_user)
        500 Internal Server Error
    """
    user = set_user()
    #if not is_localhost():
    #    abort_403()
    try:
        filename = 'test_uws_db.sqlite'
        with open(filename) as f:
            sql = f.read()
        db = storage.__dict__[STORAGE]()
        db.cursor.executescript(sql)
        db.conn.commit()
        logger.info('Database initialized using ' + filename)
    except:
        abort_500_except()
    redirect('/show_db', 303)


@app.route('/show_db')
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
        logger.info('Show Database for ' + user)
        joblist = JobList('ctbin', user, request.url)
        return joblist.to_html()
    except:
        abort_500_except()
    return html


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
        logger.info('from {} ({}) with POST={}'.format(ip, JOB_SERVERS[ip], str(request.POST.dict)))
        if 'jobid' in request.POST:
            jobid_cluster = request.POST['jobid']
            # Get job description from DB based on jobid_cluster
            job = Job('', jobid_cluster, user, get_attributes=True, from_jobid_cluster=True)
            # Update job
            if 'phase' in request.POST:
                cur_phase = job.phase
                new_phase = request.POST['phase']
                if new_phase not in PHASES:
                    if new_phase in PHASE_CONVERT:
                        new_phase = PHASE_CONVERT[new_phase]
                    else:
                        raise UserWarning('Unknown new phase ' + new_phase + ' for job ' + job.jobid)
                # If phase=ERROR, add error message if available
                if new_phase == 'ERROR':
                    if 'error_msg' in request.POST:
                        job.change_status('ERROR', request.POST['error_msg'])
                    else:
                        job.change_status('ERROR')
                    logger.info('{} {} ERROR reported (from {})'.format(job.jobname, job.jobid, user))
                elif new_phase != cur_phase:
                    job.change_status(new_phase)
                    logger.info('{} {} phase {} --> {} (from {})'
                                ''.format(job.jobname, job.jobid, cur_phase, new_phase, user))
                else:
                    raise UserWarning('Phase is already ' + new_phase)
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
# Job List


@app.route('/<jobname>')
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
        joblist = JobList(jobname, user, request.url)
        xml_out = joblist.to_xml()
        response.content_type = 'text/xml; charset=UTF-8'
        return xml_out
    except:
        abort_500_except()


@app.post('/<jobname>')
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
    redirect('/' + jobname + '/' + jobid, 303)


# ----------
# JOB Description


@app.route('/<jobname>/<jobid>')
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


@app.delete('/<jobname>/<jobid>')
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
    redirect('/' + jobname, 303)


@app.post('/<jobname>/<jobid>')
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
    redirect('/' + jobname, 303)


# ----------
# JOB Phase


@app.route('/<jobname>/<jobid>/phase')
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


@app.post('/<jobname>/<jobid>/phase')
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
                logger.info(jobname + ' ' + jobid + ' ABORTED by user ' + user)
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
    redirect('/' + jobname + '/' + jobid, 303)


# ----------
# JOB executionduration


@app.route('/<jobname>/<jobid>/executionduration')
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


@app.post('/<jobname>/<jobid>/executionduration')
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
    redirect('/' + jobname + '/' + jobid, 303)


# ----------
# JOB destruction


@app.route('/<jobname>/<jobid>/destruction')
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


@app.post('/<jobname>/<jobid>/destruction')
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
    redirect('/' + jobname + '/' + jobid, 303)


# ----------
# JOB error


@app.route('/<jobname>/<jobid>/error')
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
# JOB quote


@app.route('/<jobname>/<jobid>/quote')
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
# JOB parameters


@app.route('/<jobname>/<jobid>/parameters')
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


@app.route('/<jobname>/<jobid>/parameters/<param>')
def get_parameter(jobname, jobid, param):
    """Get parameter <param> for job <jobid>

    Returns:
        200 OK: text/plain (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Parameter not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_parameters=True)
        # Check if param exists
        if param not in job.parameters:
            raise storage.NotFoundWarning('Parameter "{}" NOT FOUND for job "{}"'.format(param, jobid))
        # Return parameter
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.parameters[param]['value'])
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


@app.post('/<jobname>/<jobid>/parameters/<pname>')
def post_parameter(jobname, jobid, pname):
    """Change the parameter value for job <jobid>

    Returns:
        303 See other: /<jobname>/<jobid>/parameters (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get value from POST
        if 'VALUE' not in request.forms:
            raise UserWarning('VALUE keyword required')
        new_value = request.forms.get('VALUE')
        # TODO: Check if new_value format is correct (from WADL?)

        # Get job description from DB
        job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True)
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
    redirect('/' + jobname + '/' + jobid + '/parameters', 303)


# ----------
# JOB results


@app.route('/<jobname>/<jobid>/results')
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


@app.route('/<jobname>/<jobid>/results/<result>')
def get_result(jobname, jobid, result):
    """Get parameter <param> for job <jobid>

    Returns:
        200 OK: text/plain (on success)
        404 Not Found: Job not found (on NotFoundWarning)
        404 Not Found: Result not found (on NotFoundWarning)
        500 Internal Server Error (on error)
    """
    try:
        user = set_user()
        logger.info(jobname + ' ' + jobid)
        # Get job description from DB
        job = Job(jobname, jobid, user, get_results=True)
        # Check if result exists
        if result not in job.results:
            raise storage.NotFoundWarning('Result "{}" NOT FOUND for job "{}"'.format(result, jobid))
        # Return result
        response.content_type = 'text/plain; charset=UTF-8'
        return str(job.results[result]['url'])
    except storage.NotFoundWarning as e:
        abort_404(e.message)
    except:
        abort_500_except()


# ----------
# JOB owner


@app.route('/<jobname>/<jobid>/owner')
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
# test server


if __name__ == '__main__':
    # Run local web server
    run(app, host='localhost', port=8080, debug=False, reloader=True)
