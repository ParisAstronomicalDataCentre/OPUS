#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Unit tests for UWS server
"""

import pytest
import webtest

from uws_server import uws_server

test_app = webtest.TestApp(uws_server.app)  # , extra_environ=dict(REMOTE_USER='test'))

print(uws_server.SQLALCHEMY_DB)
print('{}/server{}_debug.log'.format(uws_server.LOG_PATH, uws_server.LOG_FILE_SUFFIX))

# server must have a test job (does nothing)
jobname = 'test_'


def create_job():
    request = type('MyClass', (object,), {'POST': {'runId': 'test_'}, 'files': {}})()
    job = uws_server.Job(jobname, '', uws_server.User('test_', 'test_'), from_post=request)
    job.storage.save(job)
    print('\n\nFill db with job test_ {}\n'.format(job.jobid))
    return job.jobid


@pytest.fixture
def jobid():
    return create_job()


@pytest.mark.webtest
class TestGet(object):

    def assert_status(self, url, status, content_type=''):
        if status in [404, 405]:
            response = test_app.get(url, status=status)
        else:
            response = test_app.get(url)
        print(url)
        print(' --> ' + response.status)
        assert (response.status_int == status)
        if content_type:
            assert (response.headers['content-type'] == content_type)

    def test_get(self, jobid):
        # Test GET with job 22222222-e656-b924-c14a-fbd02f9ebaa9
        #jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'

        url = '/rest/' + jobname
        self.assert_status(url, 200, 'text/xml; charset=UTF-8')

        url = '/rest/' + jobname + '/bad_jobid'
        self.assert_status(url, 404)

        url = '/rest/' + jobname + '/' + jobid
        self.assert_status(url, 200, 'text/xml; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/bad_attribute'
        self.assert_status(url, 405)

        url = '/rest/' + jobname + '/' + jobid + '/phase'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/executionduration'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/destruction'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/error'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/quote'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/parameters'
        self.assert_status(url, 200, 'text/xml; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/parameters/input'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/results'
        self.assert_status(url, 200, 'text/xml; charset=UTF-8')

        #url = '/rest/' + jobname + '/' + jobid + '/results/output'
        #self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/owner'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')


class TestJobUpdate(object):
    """Test attribute updates"""

    def assert_job_attribute(self, jobid, attribute, value):
        url = '/rest/' + jobname + '/' + jobid + '/' + attribute
        response = test_app.get(url)
        assert (response.text == value)

    def test_update(self, jobid):
        # Update execution duration
        #jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/rest/' + jobname + '/' + jobid + '/executionduration'
        post = {'BAD_KEY': '120'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'EXECUTIONDURATION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'EXECUTIONDURATION': '120'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert('/' + jobname + '/' + jobid in response.location)
        self.assert_job_attribute(jobid, 'executionduration', '120')
        # Update destruction time
        url = '/rest/' + jobname + '/' + jobid + '/destruction'
        post = {'BAD_KEY': '2016-01-01T00:00:00'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'DESTRUCTION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'DESTRUCTION': '2016-01-01 00:00:00'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'DESTRUCTION': '2016-01-01T00:00:00'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname + '/' + jobid in response.location)
        self.assert_job_attribute(jobid, 'destruction', '2016-01-01T00:00:00')
        post = {'DESTRUCTION': '2016-01-01T00:00:00.55555'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname + '/' + jobid in response.location)
        self.assert_job_attribute(jobid, 'destruction', '2016-01-01T00:00:00')


class TestJobUpdateParam(object):
    """Test attribute updates"""

    def assert_job_attribute(self, jobid, attribute, value):
        url = '/rest/' + jobname + '/' + jobid + '/' + attribute
        response = test_app.get(url)
        assert (response.text == value)

    def test_update_param(self, jobid):
        # Change parameter
        url = '/rest/' + jobname + '/' + jobid + '/parameters/input'
        post = {'BAD_KEY': 'Testing'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        self.assert_job_attribute(jobid, 'parameters/input', 'test_')
        post = {'VALUE': 'test_updated'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname + '/' + jobid in response.location)
        self.assert_job_attribute(jobid, 'parameters/input', 'test_updated')
        # Change parameter of COMPLETED job
        job = uws_server.Job(jobname, jobid, uws_server.User('test_', 'test_'))
        job.change_status('COMPLETED')
        job.storage.save(job)
        url = '/rest/' + jobname + '/' + jobid + '/parameters/input'
        post = {'VALUE': 'test_completed'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        self.assert_job_attribute(jobid, 'parameters/input', 'test_updated')


class TestJobAbort(object):
    """Test abort command on jobs (COMPLETED jobs cannot be aborted)"""

    def setUp(self):
        print('\n***** TestJobAbort *****')

    def assert_job_phase(self, jobid, phase):
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        assert (response.text == phase)

    def test_abort(self, jobid):
        # Abort PENDING job
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname + '/' + jobid in response.location)
        self.assert_job_phase(jobid, 'ABORTED')
        # Abort EXECUTING job
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User('test_', 'test_'))
        job.change_status('EXECUTING')
        job.storage.save(job)
        print('Job phase is {}'.format(job.phase))
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname + '/' + jobid in response.location)
        self.assert_job_phase(jobid, 'ABORTED')
        # Abort COMPLETED job (should return HTTP Error 500)
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User('test_', 'test_'))
        job.change_status('COMPLETED')
        job.storage.save(job)
        print('Job phase is {}'.format(job.phase))
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        self.assert_job_phase(jobid, 'COMPLETED')


class TestJobDelete(object):
    """Test delete command on jobs"""

    def test_delete(self, jobid):
        # Delete PENDING job
        url = '/rest/' + jobname + '/' + jobid
        post = {'ACTION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'BAD_KEY': 'DELETE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        post = {'ACTION': 'DELETE'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname in response.location)
        # Delete EXECUTING job
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User('test_', 'test_'))
        job.change_status('EXECUTING')
        job.storage.save(job)
        print('Job phase is {}'.format(job.phase))
        url = '/rest/' + jobname + '/' + jobid
        response = test_app.delete(url, post)
        print(url + ' DELETE')
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname in response.location)
        # Delete COMPLETED job
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User('test_', 'test_'))
        job.change_status('COMPLETED')
        job.storage.save(job)
        print('Job phase is {}'.format(job.phase))
        url = '/rest/' + jobname + '/' + jobid
        response = test_app.delete(url, post)
        print(url + ' DELETE')
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname in response.location)


class TestJobSequence(object):
    """Test default sequence for a job: creation, start, executing, completed"""

    def assert_job_phase(self, jobid, phase):
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        assert (response.text == phase)

    def test_job_sequence(self, jobid):
        # Create job
        url = '/rest/' + jobname + ''
        post = {'input': 'test_start'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/' + jobname + '/' in response.location)
        jobid = response.location.split('/')[-1]
        self.assert_job_phase(jobid, 'PENDING')
        # Start job
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        self.assert_job_phase(jobid, 'PENDING')
        post = {'BAD_KEY': 'RUN'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        assert (response.status_int == 500)
        self.assert_job_phase(jobid, 'PENDING')
        post = {'PHASE': 'RUN'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        assert (response.status_int == 303)
        assert ('/rest/' + jobname + '/' + jobid in response.location)
        self.assert_job_phase(jobid, 'QUEUED')
        # job_event EXECUTING
        url = '/handler/job_event'
        post = {'jobid': '0', 'phase': 'EXECUTING'}
        response = test_app.post(url, post, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print(url)
        print(' --> ' + response.status)
        assert (response.status_int == 200)
        assert (response.text == '')
        self.assert_job_phase(jobid, 'EXECUTING')
        # job_event COMPLETED
        post = {'jobid': '0', 'phase': 'COMPLETED'}
        response = test_app.post(url, post, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print(url)
        print(' --> ' + response.status)
        assert (response.status_int == 200)
        assert (response.text == '')
        self.assert_job_phase(jobid, 'COMPLETED')

