#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from webtest import TestApp

# Redefine LOG_FILE, DB_FILE, MANAGER
LOG_FILE = 'test_uws_server.log'
DB_FILE = 'test_uws_server.db'
MANAGER = 'Manager'
import uws_server

test_app = TestApp(uws_server.app, extra_environ=dict(REMOTE_USER='test'))

jobname = 'ctbin'


class TestGet(unittest.TestCase):

    def setUp(self):
        print '\n***** TestGet *****'

    def test_get(self):
        # Initialize db, must be localhost
        response = test_app.get('/init_db', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/show_db')
        print 'DB initialized'
        # Test GET
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/html; charset=UTF-8')
        url = '/' + jobname
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/xml; charset=UTF-8')
        url = '/' + jobname + '/bad_jobid'
        response = test_app.get(url, status=404)  # need to tell WebTest to expect a status 404
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 404)
        url = '/' + jobname + '/' + jobid
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/xml; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/bad_attribute'
        response = test_app.get(url, status=404)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 404)
        url = '/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/executionduration'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/destruction'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/error'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/quote'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/parameters'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/xml; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/parameters/evfile'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/results'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/xml; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/results/0'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')
        url = '/' + jobname + '/' + jobid + '/owner'
        response = test_app.get(url)
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=UTF-8')


class TestJobUpdate(unittest.TestCase):
    """Test attribute updates"""

    def setUp(self):
        print '\n***** TestJobUpdate *****'

    def assert_job_attribute(self, jobid, attribute, value):
        url = '/' + jobname + '/' + jobid + '/' + attribute
        response = test_app.get(url)
        self.assertEqual(response.text, value)

    def test_update(self):
        # Initialize db, must be localhost
        response = test_app.get('/init_db', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print 'DB initialized'
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/show_db')
        # Update execution duration
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/' + jobname + '/' + jobid + '/executionduration'
        post = {'BAD_KEY': '120'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'EXECUTIONDURATION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'EXECUTIONDURATION': '120'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'executionduration', '120')
        # Update destruction time
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/' + jobname + '/' + jobid + '/destruction'
        post = {'BAD_KEY': '2016-01-01T00:00:00'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'DESTRUCTION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'DESTRUCTION': '2016-01-01 00:00:00'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'DESTRUCTION': '2016-01-01T00:00:00'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'destruction', '2016-01-01T00:00:00')
        post = {'DESTRUCTION': '2016-01-01T00:00:00.55555'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'destruction', '2016-01-01T00:00:00')


class TestJobUpdateParam(unittest.TestCase):
    """Test attribute updates"""

    def setUp(self):
        print '\n***** TestJobUpdateParam *****'

    def assert_job_attribute(self, jobid, attribute, value):
        url = '/' + jobname + '/' + jobid + '/' + attribute
        response = test_app.get(url)
        self.assertEqual(response.text, value)

    def test_update_param(self):
        # Initialize db, must be localhost
        response = test_app.get('/init_db', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print 'DB initialized'
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/show_db')
        # Change parameter
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/' + jobname + '/' + jobid + '/parameters/enumbins'
        post = {'BAD_KEY': '5'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        self.assert_job_attribute(jobid, 'parameters/enumbins', '1')
        post = {'VALUE': '5'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_attribute(jobid, 'parameters/enumbins', '5')
        # Change parameter of COMPLETED job
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/' + jobname + '/' + jobid + '/parameters/enumbins'
        post = {'VALUE': '5'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        self.assert_job_attribute(jobid, 'parameters/enumbins', '1')


class TestJobAbort(unittest.TestCase):
    """Test abort command on jobs (COMPLETED jobs cannot be aborted)"""

    def setUp(self):
        print '\n***** TestJobAbort *****'

    def assert_job_phase(self, jobid, phase):
        url = '/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        self.assertEqual(response.text, phase)

    def test_abort(self):
        # Initialize db, must be localhost
        response = test_app.get('/init_db', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print 'DB initialized'
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/show_db')
        # Abort PENDING job
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_phase(jobid, 'ABORTED')
        # Abort EXECUTING job
        jobid = '11111111-9c85-4873-a4b1-8d7e5e91ed57'
        url = '/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_phase(jobid, 'ABORTED')
        # Abort COMPLETED job (should return HTTP Error 500)
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'ABORT'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        self.assert_job_phase(jobid, 'COMPLETED')


class TestJobDelete(unittest.TestCase):
    """Test delete command on jobs"""

    def setUp(self):
        print '\n***** TestJobDelete *****'

    def test_delete(self):
        # Initialize db, must be localhost
        response = test_app.get('/init_db', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print 'DB initialized'
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/show_db')
        # Delete PENDING job
        jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = '/' + jobname + '/' + jobid
        post = {'ACTION': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'BAD_KEY': 'DELETE'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        post = {'ACTION': 'DELETE'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname)
        # Delete EXECUTING job
        jobid = '11111111-9c85-4873-a4b1-8d7e5e91ed57'
        url = '/' + jobname + '/' + jobid
        response = test_app.delete(url, post)
        print url + ' DELETE'
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname)
        # Delete COMPLETED job
        jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'
        url = '/' + jobname + '/' + jobid
        response = test_app.delete(url, post)
        print url + ' DELETE'
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname)


class TestJobSequence(unittest.TestCase):
    """Test default sequence for a job: creation, start, executing, completed"""

    def setUp(self):
        print '\n***** TestJobSequence *****'

    def assert_job_phase(self, jobid, phase):
        url = '/' + jobname + '/' + jobid + '/phase'
        response = test_app.get(url)
        self.assertEqual(response.text, phase)

    def test_job_sequence(self):
        # Initialize db, must be localhost
        response = test_app.get('/init_db', extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print 'DB initialized'
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/show_db')
        # Create job
        url = '/' + jobname + ''
        post = {'evfile': 'test.fits', 'enumbins': 2}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/')
        jobid = response.location.split('/')[-1]
        self.assert_job_phase(jobid, 'PENDING')
        # Start job
        url = '/' + jobname + '/' + jobid + '/phase'
        post = {'PHASE': 'BAD_VALUE'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        self.assert_job_phase(jobid, 'PENDING')
        post = {'BAD_KEY': 'RUN'}
        response = test_app.post(url, post, status=500)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.html.pre.string
        self.assertEqual(response.status_int, 500)
        self.assert_job_phase(jobid, 'PENDING')
        post = {'PHASE': 'RUN'}
        response = test_app.post(url, post)
        print url + ' ' + str(post)
        print ' --> ' + response.status
        print ' --> ' + response.location
        self.assertEqual(response.status_int, 303)
        self.assertRegexpMatches(response.location, '/' + jobname + '/' + jobid)
        self.assert_job_phase(jobid, 'QUEUED')
        # job_event EXECUTING
        url = '/job_event/0?PHASE=EXECUTING'
        response = test_app.get(url, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.text, '')
        self.assert_job_phase(jobid, 'EXECUTING')
        # job_event COMPLETED
        url = '/job_event/0?PHASE=COMPLETED'
        response = test_app.get(url, extra_environ=dict(REMOTE_ADDR='127.0.0.1'))
        print url
        print ' --> ' + response.status
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.text, '')
        self.assert_job_phase(jobid, 'COMPLETED')


# If running this file, run the tests
# invoke with `python -m unittest discover`
if __name__ == '__main__':
    # Run tests
    unittest.main()
