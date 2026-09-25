#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Unit tests for UWS server
"""

import base64
import os
import shutil

import pytest
import webtest

from uws_server import uws_server

test_app = webtest.TestApp(uws_server.app)  # , extra_environ=dict(REMOTE_USER='test'))

settings = uws_server.settings
print(settings.SQLALCHEMY_DB)
print(f"{settings.LOG_PATH}/server{settings.LOG_FILE_SUFFIX}_debug.log")

# server must have a test job (does nothing)
jobname = "test_"
UWS_EP = settings.UWS_SERVER_ENDPOINT


def create_job():
    request = type("MyClass", (object,), {"POST": {"runId": "test_"}, "files": {}})()
    job = uws_server.Job(
        jobname, "", uws_server.User("test_", "test_"), from_post=request
    )
    try:
        job.storage.save(job)
        print(f"\n\nFill db with job test_ {job.jobid}\n")
        return job.jobid
    finally:
        job.close()


@pytest.fixture
def jobid():
    return create_job()


class TestGet:

    def assert_status(self, url, status, content_type=""):
        if status in [404, 405]:
            response = test_app.get(url, status=status)
        else:
            response = test_app.get(url)
        print(url)
        print(" --> " + response.status)
        assert response.status_int == status
        if content_type:
            assert response.headers["content-type"] == content_type

    def test_get(self, jobid):
        # Test GET with job 22222222-e656-b924-c14a-fbd02f9ebaa9
        # jobid = '22222222-e656-b924-c14a-fbd02f9ebaa9'

        url = UWS_EP + "/" + jobname
        self.assert_status(url, 200, "text/xml; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/bad_jobid"
        self.assert_status(url, 404)

        url = UWS_EP + "/" + jobname + "/" + jobid
        self.assert_status(url, 200, "text/xml; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/bad_attribute"
        self.assert_status(url, 405)

        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/executionduration"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/destruction"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/error"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/quote"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/parameters"
        self.assert_status(url, 200, "text/xml; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/parameters/input"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")

        url = UWS_EP + "/" + jobname + "/" + jobid + "/results"
        self.assert_status(url, 200, "text/xml; charset=UTF-8")

        # url = UWS_EP + '/' + jobname + '/' + jobid + '/results/output'
        # self.assert_status(url, 200, 'text/plain; charset=UTF-8')

        url = UWS_EP + "/" + jobname + "/" + jobid + "/owner"
        self.assert_status(url, 200, "text/plain; charset=UTF-8")


class TestJobUpdate:
    """Test attribute updates"""

    def assert_job_attribute(self, jobid, attribute, value):
        url = UWS_EP + "/" + jobname + "/" + jobid + "/" + attribute
        response = test_app.get(url)
        assert response.text == value

    def test_update(self, jobid):
        # Update execution duration
        # jobid = '00000000-dbf3-6b04-b1e7-28d47ad32794'
        url = UWS_EP + "/" + jobname + "/" + jobid + "/executionduration"
        post = {"BAD_KEY": "120"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"EXECUTIONDURATION": "BAD_VALUE"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"EXECUTIONDURATION": "120"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" + jobid in response.location
        self.assert_job_attribute(jobid, "executionduration", "120")
        # Update destruction time
        url = UWS_EP + "/" + jobname + "/" + jobid + "/destruction"
        post = {"BAD_KEY": "2016-01-01T00:00:00"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"DESTRUCTION": "BAD_VALUE"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"DESTRUCTION": "2016-01-01 00:00:00"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"DESTRUCTION": "2016-01-01T00:00:00"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" + jobid in response.location
        self.assert_job_attribute(jobid, "destruction", "2016-01-01T00:00:00")
        post = {"DESTRUCTION": "2016-01-01T00:00:00.55555"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" + jobid in response.location
        self.assert_job_attribute(jobid, "destruction", "2016-01-01T00:00:00")


class TestJobUpdateParam:
    """Test attribute updates"""

    def assert_job_attribute(self, jobid, attribute, value):
        url = UWS_EP + "/" + jobname + "/" + jobid + "/" + attribute
        response = test_app.get(url)
        assert response.text == value

    def test_update_param(self, jobid):
        # Change parameter
        url = UWS_EP + "/" + jobname + "/" + jobid + "/parameters/input"
        post = {"BAD_KEY": "Testing"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        self.assert_job_attribute(jobid, "parameters/input", "test_")
        post = {"VALUE": "test_updated"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" + jobid in response.location
        self.assert_job_attribute(jobid, "parameters/input", "test_updated")
        # Value too long to be stored
        post = {"VALUE": "x" * 256}
        response = test_app.post(url, post, status=400)
        assert response.status_int == 400
        self.assert_job_attribute(jobid, "parameters/input", "test_updated")
        # Change parameter of COMPLETED job
        job = uws_server.Job(jobname, jobid, uws_server.User("test_", "test_"))
        job.change_status("COMPLETED")
        job.storage.save(job)
        url = UWS_EP + "/" + jobname + "/" + jobid + "/parameters/input"
        post = {"VALUE": "test_completed"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        self.assert_job_attribute(jobid, "parameters/input", "test_updated")


class TestParameterLength:
    """Test creation of jobs with parameter values too long to be stored"""

    def test_create_too_long(self):
        url = UWS_EP + "/" + jobname
        for post in [{"runId": "r" * 65}, {"input": "x" * 256}]:
            response = test_app.post(url, post, status=400)
            print(url + " " + str({k: len(v) for k, v in post.items()}))
            print(" --> " + response.status)
            assert response.status_int == 400
            assert "too long" in response.text


class TestUsers:
    """A user is identified by name + token: same name, other token = other account"""

    def test_accounts_by_name_and_token(self):
        job_storage = getattr(uws_server.storage, settings.STORAGE + "JobStorage")()
        name = "user_" + settings.new_token()[:8]
        job_storage.add_user(name, token="token1", roles="test_")
        # A request with another token creates another account, without the roles
        job_storage.add_user(name, token="token2")
        assert len(job_storage.get_users(name=name)) == 2
        assert job_storage.has_role(name, "token1", role="test_")
        assert not job_storage.has_role(name, "token2", role="test_")
        # The first account is unchanged
        assert job_storage.get_users(name=name, token="token1")[0]["roles"] == "test_"

    def test_roles(self):
        job_storage = getattr(uws_server.storage, settings.STORAGE + "JobStorage")()
        name = "user_" + settings.new_token()[:8]
        job_storage.add_user(name, token="token1", roles="test_")
        job_storage.add_role(name, "token1", role="other_job")
        assert job_storage.has_role(name, "token1", role="other_job")
        job_storage.remove_role(name, "token1", role="other_job")
        assert not job_storage.has_role(name, "token1", role="other_job")
        assert job_storage.has_role(name, "token1", role="test_")


class TestPermissions:
    """Job definitions listed for a user, with CHECK_PERMISSIONS (roles = job names, or all)"""

    def test_jdl_list_with_roles(self, monkeypatch):
        # a job definition and its script in the test VAR_PATH (a job is listed if both exist)
        test_jobs = os.path.join(os.path.dirname(__file__), os.pardir, "test_jobs")
        shutil.copy(os.path.join(test_jobs, "test_activity_1_vot.xml"), settings.JDL_PATH + "/votable/")
        with open(settings.SCRIPTS_PATH + "/test_activity_1.sh", "w") as f:
            f.write("echo $text > $output\n")
        monkeypatch.setattr(settings, "CHECK_PERMISSIONS", True)
        job_storage = getattr(uws_server.storage, settings.STORAGE + "JobStorage")()
        # (other job definitions may exist, e.g. installed by test_jobs.py)
        for roles, expected in [("all", None), ("test_activity_1", ["test_activity_1"]), ("", [])]:
            name = "user_" + settings.new_token()[:8]
            job_storage.add_user(name, token="token", roles=roles)
            auth = base64.b64encode(f"{name}:token".encode()).decode()
            response = test_app.get("/jdl", extra_environ={"HTTP_AUTHORIZATION": "Basic " + auth})
            print(f"roles={roles!r} --> {response.json['jobnames']}")
            if expected is None:  # all the jobs
                assert "test_activity_1" in response.json["jobnames"]
            else:
                assert response.json["jobnames"] == expected


class TestJobAbort:
    """Test abort command on jobs (COMPLETED jobs cannot be aborted)"""

    def setUp(self):
        print("\n***** TestJobAbort *****")

    def assert_job_phase(self, jobid, phase):
        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        response = test_app.get(url)
        assert response.text == phase

    def test_abort(self, jobid):
        # Abort PENDING job
        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        post = {"PHASE": "ABORT"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" + jobid in response.location
        self.assert_job_phase(jobid, "ABORTED")
        # Abort EXECUTING job
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User("test_", "test_"))
        job.change_status("EXECUTING")
        job.storage.save(job)
        print(f"Job phase is {job.phase}")
        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        post = {"PHASE": "ABORT"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" + jobid in response.location
        self.assert_job_phase(jobid, "ABORTED")
        # Abort COMPLETED job (should return HTTP Error 500)
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User("test_", "test_"))
        job.change_status("COMPLETED")
        job.storage.save(job)
        print(f"Job phase is {job.phase}")
        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        post = {"PHASE": "ABORT"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        self.assert_job_phase(jobid, "COMPLETED")


class TestJobDelete:
    """Test delete command on jobs"""

    def test_delete(self, jobid):
        # Delete PENDING job
        url = UWS_EP + "/" + jobname + "/" + jobid
        post = {"ACTION": "BAD_VALUE"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"BAD_KEY": "DELETE"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        post = {"ACTION": "DELETE"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname in response.location
        # Delete EXECUTING job
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User("test_", "test_"))
        job.change_status("EXECUTING")
        job.storage.save(job)
        print(f"Job phase is {job.phase}")
        url = UWS_EP + "/" + jobname + "/" + jobid
        response = test_app.delete(url, post)
        print(url + " DELETE")
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname in response.location
        # Delete COMPLETED job
        jobid = create_job()
        job = uws_server.Job(jobname, jobid, uws_server.User("test_", "test_"))
        job.change_status("COMPLETED")
        job.storage.save(job)
        print(f"Job phase is {job.phase}")
        url = UWS_EP + "/" + jobname + "/" + jobid
        response = test_app.delete(url, post)
        print(url + " DELETE")
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname in response.location


class TestJobSequence:
    """Test default sequence for a job: creation, start, executing, completed"""

    def assert_job_phase(self, jobid, phase):
        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        response = test_app.get(url)
        assert response.text == phase

    def test_job_sequence(self, jobid):
        # Create job
        url = UWS_EP + "/" + jobname + ""
        post = {"input": "test_start"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert "/" + jobname + "/" in response.location
        jobid = response.location.split("/")[-1]
        self.assert_job_phase(jobid, "PENDING")
        # Start job
        url = UWS_EP + "/" + jobname + "/" + jobid + "/phase"
        post = {"PHASE": "BAD_VALUE"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        self.assert_job_phase(jobid, "PENDING")
        post = {"BAD_KEY": "RUN"}
        response = test_app.post(url, post, status=500)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.html.pre.string)
        assert response.status_int == 500
        self.assert_job_phase(jobid, "PENDING")
        post = {"PHASE": "RUN"}
        response = test_app.post(url, post)
        print(url + " " + str(post))
        print(" --> " + response.status)
        print(" --> " + response.location)
        assert response.status_int == 303
        assert UWS_EP + "/" + jobname + "/" + jobid in response.location
        self.assert_job_phase(jobid, "QUEUED")
        # job_event EXECUTING
        url = "/handler/job_event"
        post = {"jobid": "0", "phase": "EXECUTING"}
        response = test_app.post(url, post, extra_environ={"REMOTE_ADDR": "127.0.0.1"})
        print(url)
        print(" --> " + response.status)
        assert response.status_int == 200
        assert response.text == ""
        self.assert_job_phase(jobid, "EXECUTING")
        # job_event COMPLETED
        post = {"jobid": "0", "phase": "COMPLETED"}
        response = test_app.post(url, post, extra_environ={"REMOTE_ADDR": "127.0.0.1"})
        print(url)
        print(" --> " + response.status)
        assert response.status_int == 200
        assert response.text == ""
        self.assert_job_phase(jobid, "COMPLETED")
