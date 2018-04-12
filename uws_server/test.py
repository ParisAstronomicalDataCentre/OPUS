#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Unit tests for UWS server
"""

import unittest
from webtest import TestApp

# Redefine LOG_FILE, SQLITE_FILE, MANAGER
SQLITE_FILE_NAME = 'job_database_test.db'
LOG_FILE_SUFFIX = '_test'
MANAGER = ''

import uws_server

test_app = TestApp(uws_server.app)  # , extra_environ=dict(REMOTE_USER='test'))

jobname = 'ctbin'


class TestGet(unittest.TestCase):

    def setUp(self):
        print('\n***** TestGet *****')

    def assert_status(self, url, status, content_type=''):
        if status in [404, 405]:
            response = test_app.get(url, status=status)
        else:
            response = test_app.get(url)
        print(url)
        print(' --> ' + response.status)
        self.assertEqual(response.status_int, status)
        if content_type:
            self.assertEqual(response.headers['content-type'], content_type)

    def test_get(self):
        # Initialize db, must be localhost
        response = test_app.get('/db/test', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/db/show')
        print('DB initialized')
        # Test GET with job 22222222-e656-b924-c14a-fbd02f9ebaa9
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'

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

        url = '/rest/' + jobname + '/' + jobid + '/results/output'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = '/rest/' + jobname + '/' + jobid + '/owner'
        self.assert_status(url, 200, 'text/plain; charset=UTF-8')


class TestJobUpdate(unittest.TestCase):
    """Test attribute updates"""

    def setUp(self):
        print('\n***** TestJobUpdate *****')

    def assert_job_attribute(self, jobid, attribute, value):
        url = '/rest/' + jobname + '/' + jobid + '/' + attribute
        response = test_app.get(url)
        self.assertEqual(response.text, value)

    def test_update(self):
        # Initialize db, must be localhost
        response = test_app.get('/db/test', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print('DB initialized')
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/db/show')
        # Update execution duration
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/rest/' + jobname + '/' + jobid + '/executionduration'
        post = {'BAD_KEY': '120'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'EXECUTIONDURATION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'EXECUTIONDURATION': '120'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'executionduration', '120')
        # Update destruction time
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/rest/' + jobname + '/' + jobid + '/destruction'
        post = {'BAD_KEY': '2016-01-01T00:00:00'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'DESTRUCTION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'DESTRUCTION': '2016-01-01 00:00:00'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'DESTRUCTION': '2016-01-01T00:00:00'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'destruction', '2016-01-01T00:00:00')
        post = {'DESTRUCTION': '2016-01-01T00:00:00.55555'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'destruction', '2016-01-01T00:00:00')


class TestJobUpdateParam(unittest.TestCase):
    """Test attribute updates"""

    def setUp(self):
        print('\n***** TestJobUpdateParam *****')

    def assert_job_attribute(self, jobid, attribute, value):
        url = '/rest/' + jobname + '/' + jobid + '/' + attribute
        response = test_app.get(url)
        self.assertEqual(response.text, value)

    def test_update_param(self):
        # Initialize db, must be localhost
        response = test_app.get('/db/test', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print('DB initialized')
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/db/show')
        # Change parameter
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/rest/' + jobname + '/' + jobid + '/parameters/input'
        post = {'BAD_KEY': 'Testing'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        self.assert_job_attribute(jobid, 'parameters/input', 'Test 0')
        post = {'VALUE': 'Testing'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'parameters/input', 'Testing')
        # Change parameter of COMPLETED job
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/rest/' + jobname + '/' + jobid + '/parameters/input'
        post = {'VALUE': 'Testing'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        self.assert_job_attribute(jobid, 'parameters/input', 'Test 2')


class TestJobAbort(unittest.TestCase):
    """Test abort command on jobs (COMPLETED jobs cannot be aborted)"""

    def setUp(self):
        print('\n***** TestJobAbort *****')

    def assert_job_phase(self, jobid, phase):
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        self.assertEqual(response.text, phase)

    def test_abort(self):
        # Initialize db, must be localhost
        response = test_app.get('/db/test', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print('DB initialized')
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/db/show')
        # Abort PENDING job
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_phase(jobid, 'ABORTED')
        # Abort EXECUTING job
        jobid = '11111111-9c85-4873-a4b1-8d7e5e91ed57'
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_phase(jobid, 'ABORTED')
        # Abort COMPLETED job (should return HTTP Error 500)
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        self.assert_job_phase(jobid, 'COMPLETED')


class TestJobDelete(unittest.TestCase):
    """Test delete command on jobs"""

    def setUp(self):
        print('\n***** TestJobDelete *****')

    def test_delete(self):
        # Initialize db, must be localhost
        response = test_app.get('/db/test', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print('DB initialized')
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/db/show')
        # Delete PENDING job
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/rest/' + jobname + '/' + jobid
        post = {'ACTION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'BAD_KEY': 'DELETE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        post = {'ACTION': 'DELETE'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname)
        # Delete EXECUTING job
        jobid = '11111111-9c85-4873-a4b1-8d7e5e91ed57'
        url = '/rest/' + jobname + '/' + jobid
        response = test_app.delete(url, post)
        print(url + ' DELETE')
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname)
        # Delete COMPLETED job
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/rest/' + jobname + '/' + jobid
        response = test_app.delete(url, post)
        print(url + ' DELETE')
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname)


class TestJobSequence(unittest.TestCase):
    """Test default sequence for a job: creation, start, executing, completed"""

    def setUp(self):
        print('\n***** TestJobSequence *****')

    def assert_job_phase(self, jobid, phase):
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        self.assertEqual(response.text, phase)

    def test_job_sequence(self):
        # Initialize db, must be localhost
        response = test_app.get('/db/test', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print('DB initialized')
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/db/show')
        # Create job
        url = '/rest/' + jobname + ''
        post = {'input': 'Testing'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/')
        jobid = response.location.split('/')[-1]
        self.assert_job_phase(jobid, 'PENDING')
        # Start job
        url = '/rest/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        self.assert_job_phase(jobid, 'PENDING')
        post = {'BAD_KEY': 'RUN'}
        response = test_app.post(url, post, status=500)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.html.pre.string)
        self.assertEqual(response.status_int, 500)
        self.assert_job_phase(jobid, 'PENDING')
        post = {'PHASE': 'RUN'}
        response = test_app.post(url, post)
        print(url + ' ' + str(post))
        print(' --> ' + response.status)
        print(' --> ' + response.location)
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/rest/' + jobname + '/' + jobid)
        self.assert_job_phase(jobid, 'QUEUED')
        # job_event EXECUTING
        url = '/handler/job_event'
        post = {'jobid': '0', 'phase': 'EXECUTING'}
        response = test_app.post(url, post, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print(url)
        print(' --> ' + response.status)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.text, '')
        self.assert_job_phase(jobid, 'EXECUTING')
        # job_event COMPLETED
        post = {'jobid': '0', 'phase': 'COMPLETED'}
        response = test_app.post(url, post, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print(url)
        print(' --> ' + response.status)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.text, '')
        self.assert_job_phase(jobid, 'COMPLETED')


# If running this file, run the tests
# invoke with `python -m unittest discover`
if __name__ == '__main__':
    # Run tests
    unittest.main()
