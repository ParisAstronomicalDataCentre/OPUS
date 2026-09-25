#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Tests of the REST routes of the UWS server, on a server running in a thread (live_server fixture):
- SCIM API used by the Server Accounts page of the client (admin only)
- UWS job attributes (execution duration, destruction time), job list filters, WAIT (blocking GET)
- access control: anonymous users, job owner (CHECK_OWNER), permissions (CHECK_PERMISSIONS)
"""

import threading
import time
import xml.etree.ElementTree as ET

import pytest
import requests

from opus_config import logs
from test_jobs import (  # noqa: F401 (server fixture)
    AUTH,
    create_job,
    job_attributes,
    server,
    wait,
)
from uws_server import storage
from uws_server.settings import settings

ADMIN = (settings.ADMIN_NAME, settings.ADMIN_TOKEN.get_secret_value())
OTHER = ("other@example.org", "other-token")


def base_url(server):  # noqa: F811 (server fixture)
    return server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]


def job_ids(server, query="", auth=AUTH):  # noqa: F811 (server fixture)
    """Job IDs of the job list of test_activity_1"""
    xml = requests.get(f"{server}/test_activity_1{query}", auth=auth).text
    return [job.get("id") or job.find("{*}jobId").text for job in ET.fromstring(xml)]


class TestScim:

    @pytest.fixture
    def scim(self, live_server):
        return f"{live_server}{settings.SCIM_ENDPOINT}"

    def test_service_description(self, scim):
        for path in ["ServiceProviderConfig", "Schemas", "ResourceTypes", "ResourceTypes/User"]:
            assert requests.get(f"{scim}/{path}").status_code == 200

    def test_admin_only(self, scim):
        assert requests.get(f"{scim}/Users", auth=AUTH).status_code == 403
        response = requests.post(f"{scim}/Users", data={"name": "intruder"}, auth=AUTH)
        assert response.status_code == 403

    def test_accounts(self, scim):
        name = f"scim{time.time_ns()}@example.org"
        # create
        response = requests.post(f"{scim}/Users", data={"name": name, "token": "token1", "roles": "job1"}, auth=ADMIN)
        assert response.status_code == 200
        user = response.json()
        assert (user["userName"], user["token"], user["roles"]) == (name, "token1", "job1")
        users = [u["userName"] for u in requests.get(f"{scim}/Users", auth=ADMIN).json()["Resources"]]
        assert name in users and settings.ADMIN_NAME not in users
        assert requests.get(f"{scim}/Users/{name}", auth=ADMIN).json()["token"] == "token1"
        # same name, other token: another account, the token is then needed
        requests.post(f"{scim}/Users", data={"name": name, "token": "token2"}, auth=ADMIN)
        assert requests.get(f"{scim}/Users/{name}", auth=ADMIN).status_code == 409
        user = requests.get(f"{scim}/Users/{name}", params={"token": "token2"}, auth=ADMIN).json()
        assert user["token"] == "token2" and not user["roles"]
        # patch roles, active and token at once
        data = {"user_token": "token1", "roles": "job1,job2", "active": "false", "token": "token3"}
        response = requests.post(f"{scim}/Users/{name}", data=data, auth=ADMIN)
        assert response.status_code == 200
        user = requests.get(f"{scim}/Users/{name}", params={"token": "token3"}, auth=ADMIN).json()
        assert (user["roles"], str(user["active"]).lower()) == ("job1,job2", "false")
        # delete
        response = requests.delete(f"{scim}/Users/{name}", data={"user_token": "token3"}, auth=ADMIN)
        assert response.status_code == 200
        assert requests.get(f"{scim}/Users/{name}", params={"token": "token3"}, auth=ADMIN).status_code == 404
        assert requests.get(f"{scim}/Users/{name}", auth=ADMIN).json()["token"] == "token2"

    def test_errors(self, scim):
        assert requests.post(f"{scim}/Users", data={}, auth=ADMIN).status_code == 500
        assert requests.get(f"{scim}/Users/unknown", auth=ADMIN).status_code == 404
        response = requests.post(f"{scim}/Users/unknown", data={"user_token": "t", "roles": "x"}, auth=ADMIN)
        assert response.status_code == 404
        assert requests.post(f"{scim}/Users/unknown", data={"roles": "x"}, auth=ADMIN).status_code == 404
        response = requests.delete(f"{scim}/Users/unknown", data={"user_token": "t"}, auth=ADMIN)
        assert response.status_code == 500


class TestJobAttributes:

    def test_execution_duration(self, server):  # noqa: F811 (server fixture)
        job_url = create_job(server, "test_activity_1", run=False, text="pending")
        assert requests.get(f"{job_url}/executionduration", auth=AUTH).text == "20"  # from the job definition
        response = requests.post(f"{job_url}/executionduration", data={"EXECUTIONDURATION": "120"}, auth=AUTH, allow_redirects=False)
        assert response.status_code == 303
        assert requests.get(f"{job_url}/executionduration", auth=AUTH).text == "120"
        assert job_attributes(job_url)["executionDuration"] == "120"
        for data in [{"EXECUTIONDURATION": "long"}, {}]:
            assert requests.post(f"{job_url}/executionduration", data=data, auth=AUTH).status_code == 500
        # only for a pending job
        requests.post(f"{job_url}/phase", data={"PHASE": "RUN"}, auth=AUTH)
        assert wait(job_url) == "COMPLETED"
        response = requests.post(f"{job_url}/executionduration", data={"EXECUTIONDURATION": "60"}, auth=AUTH)
        assert response.status_code == 500 and "PENDING" in response.text

    def test_destruction(self, server):  # noqa: F811 (server fixture)
        job_url = create_job(server, "test_activity_1", run=False, text="destruction")
        data = {"DESTRUCTION": "2099-01-02T03:04:05.678Z"}  # fraction of seconds and zone are ignored
        response = requests.post(f"{job_url}/destruction", data=data, auth=AUTH, allow_redirects=False)
        assert response.status_code == 303
        assert requests.get(f"{job_url}/destruction", auth=AUTH).text == "2099-01-02T03:04:05"
        for data in [{"DESTRUCTION": "tomorrow"}, {}]:
            assert requests.post(f"{job_url}/destruction", data=data, auth=AUTH).status_code == 500

    def test_job_list_filters(self, server):  # noqa: F811 (server fixture)
        pending = create_job(server, "test_activity_1", run=False, text="pending").split("/")[-1]
        completed = create_job(server, "test_activity_1", text="completed")
        assert wait(completed) == "COMPLETED"
        completed = completed.split("/")[-1]
        ids = job_ids(server, "?PHASE=PENDING")
        assert pending in ids and completed not in ids
        ids = job_ids(server, "?PHASE=PENDING&PHASE=COMPLETED")
        assert pending in ids and completed in ids
        assert len(job_ids(server, "?LAST=1")) == 1
        assert pending not in job_ids(server, "?AFTER=2099-01-01T00:00:00")


class TestWait:

    def test_wait_timeout(self, server):  # noqa: F811 (server fixture)
        job_url = create_job(server, "test_activity_1", text="slow wait")
        assert wait(job_url, phases=("EXECUTING",)) == "EXECUTING"
        try:
            start = time.time()
            root = ET.fromstring(requests.get(job_url, params={"WAIT": 1}, auth=AUTH).text)
            assert 1 <= time.time() - start < 5
            assert root.find("{*}phase").text == "EXECUTING"
            # the client knows another phase: no wait
            start = time.time()
            requests.get(job_url, params={"WAIT": 10, "PHASE": "QUEUED"}, auth=AUTH)
            assert time.time() - start < 1
        finally:
            requests.post(f"{job_url}/phase", data={"PHASE": "ABORT"}, auth=AUTH)

    def test_wait_phase_change(self, server):  # noqa: F811 (server fixture)
        job_url = create_job(server, "test_activity_1", text="slow change")
        assert wait(job_url, phases=("EXECUTING",)) == "EXECUTING"
        abort = threading.Timer(0.5, requests.post, args=(f"{job_url}/phase",), kwargs={"data": {"PHASE": "ABORT"}, "auth": AUTH})
        abort.start()
        start = time.time()
        root = ET.fromstring(requests.get(job_url, params={"WAIT": 5, "PHASE": "EXECUTING"}, auth=AUTH).text)
        abort.join()
        assert time.time() - start < 3  # returns as soon as the phase changes
        assert root.find("{*}phase").text == "ABORTED"

    def test_requests_during_wait(self, server):  # noqa: F811 (server fixture)
        """The requests are handled in parallel (pool of threads)"""
        job_url = create_job(server, "test_activity_1", text="slow parallel")
        assert wait(job_url, phases=("EXECUTING",)) == "EXECUTING"
        waiting = threading.Thread(target=requests.get, args=(job_url,), kwargs={"params": {"WAIT": 3}, "auth": AUTH})
        waiting.start()
        try:
            time.sleep(0.3)
            start = time.time()
            assert requests.get(f"{job_url}/phase", auth=AUTH).text == "EXECUTING"
            assert time.time() - start < 1
        finally:
            requests.post(f"{job_url}/phase", data={"PHASE": "ABORT"}, auth=AUTH)
            waiting.join()

    def test_no_wait_for_terminal_phase(self, server):  # noqa: F811 (server fixture)
        job_url = create_job(server, "test_activity_1", text="done")
        assert wait(job_url) == "COMPLETED"
        start = time.time()
        requests.get(job_url, params={"WAIT": 10}, auth=AUTH)
        assert time.time() - start < 1


class TestAccess:

    def test_anonymous(self, server, monkeypatch):  # noqa: F811 (server fixture)
        monkeypatch.setattr(settings, "ALLOW_ANONYMOUS", False)
        assert requests.get(f"{server}/test_activity_1").status_code == 403
        monkeypatch.setattr(settings, "ALLOW_ANONYMOUS", True)
        assert requests.get(f"{server}/test_activity_1").status_code == 200

    def test_owner(self, server, monkeypatch):  # noqa: F811 (server fixture)
        job_url = create_job(server, "test_activity_1", text="owned")
        assert wait(job_url) == "COMPLETED"
        jobid = job_url.split("/")[-1]
        monkeypatch.setattr(settings, "CHECK_OWNER", True)
        # another user, or the same name with another token (another account)
        for auth in [OTHER, (AUTH[0], "another-token")]:
            assert requests.get(job_url, auth=auth).status_code == 403
            assert requests.get(f"{job_url}/results/output", auth=auth).status_code == 403
            assert requests.post(f"{job_url}/phase", data={"PHASE": "ABORT"}, auth=auth).status_code == 403
            assert requests.delete(job_url, auth=auth).status_code == 403
            assert jobid not in job_ids(server, auth=auth)
        # the owner and the admin
        assert requests.get(job_url, auth=AUTH).status_code == 200
        assert requests.get(job_url, auth=ADMIN).status_code == 200
        assert jobid in job_ids(server, auth=ADMIN)
        # without CHECK_OWNER, the job can be accessed but is not listed
        monkeypatch.setattr(settings, "CHECK_OWNER", False)
        assert requests.get(job_url, auth=OTHER).status_code == 200
        assert jobid not in job_ids(server, auth=OTHER)

    def test_store_owner(self, server, monkeypatch):  # noqa: F811 (server fixture)
        """A result file (/store) can be downloaded by its owner (name + token)"""
        job_url = create_job(server, "test_activity_1", text="stored")
        assert wait(job_url) == "COMPLETED"
        store_url = requests.get(f"{job_url}/results/output", auth=AUTH).text
        monkeypatch.setattr(settings, "CHECK_OWNER", True)
        for auth in [OTHER, (AUTH[0], "another-token")]:
            assert requests.get(store_url, auth=auth).status_code == 403
        for auth in [AUTH, ADMIN]:
            response = requests.get(store_url, auth=auth)
            assert response.status_code == 200 and response.text == "stored\n"
        # entity registered by a previous version, without owner token: checked by owner name
        entity_id = store_url.split("ID=")[-1]
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        with job_storage.get_session() as session:
            session.query(job_storage.Entity).filter_by(entity_id=entity_id).update({"owner_token": None})
            session.commit()
        assert requests.get(store_url, auth=(AUTH[0], "another-token")).status_code == 200
        assert requests.get(store_url, auth=OTHER).status_code == 403

    def test_permissions(self, server, monkeypatch):  # noqa: F811 (server fixture)
        monkeypatch.setattr(settings, "CHECK_PERMISSIONS", True)
        name, token = f"perm{time.time_ns()}@example.org", "perm-token"
        response = requests.post(f"{server}/test_activity_1", data={"text": "x"}, auth=(name, token))
        assert response.status_code == 403
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        job_storage.add_role(name, token, role="test_activity_1")
        job_url = create_job_as(server, (name, token))
        assert phase_as(job_url, (name, token)) == "PENDING"
        # the role is given to this account only (same name, other token)
        response = requests.post(f"{server}/test_activity_1", data={"text": "x"}, auth=(name, "other"))
        assert response.status_code == 403


class TestLog:

    def test_log(self, live_server):
        url = f"{live_server}/log"
        requests.get(f"{live_server}/jdl", auth=AUTH)  # at least one line in the log
        response = requests.get(url, params={"LINES": 3}, auth=ADMIN)
        assert response.status_code == 200 and response.headers["Content-Type"].startswith("text/plain")
        assert 0 < len(response.text.splitlines()) <= 3
        for name in ["server_debug", "debug"]:
            assert requests.get(url, params={"FILE": name}, auth=ADMIN).status_code == 200
        # nginx logs (in the same directory, no nginx in the tests)
        assert requests.get(url, params={"FILE": "nginx_access"}, auth=ADMIN).status_code == 404
        assert requests.get(url, params={"FILE": "../../etc/passwd"}, auth=ADMIN).status_code == 400
        # admin only
        assert requests.get(url, auth=AUTH).status_code == 403


class TestTail:

    def test_tail(self, tmp_path):
        path = tmp_path / "test.log"
        path.write_text("".join(f"line {i}\n" for i in range(1, 30001)))  # larger than a block
        assert logs.tail(path, 3) == ["line 29998", "line 29999", "line 30000"]
        assert len(logs.tail(path, 10000)) == 10000 and logs.tail(path, 10000)[0] == "line 20001"
        path.write_text("first\nlast")  # no final newline
        assert logs.tail(path, 100) == ["first", "last"]
        path.write_text("")
        assert logs.tail(path, 5) == []

    def test_lines_param(self):
        assert [logs.lines_param(v) for v in ["20", None, "x", "0", "-5", "999999"]] == [20, 100, 100, 1, 1, 10000]


def create_job_as(server, auth):  # noqa: F811 (server fixture)
    response = requests.post(f"{server}/test_activity_1", data={"text": "x"}, auth=auth, allow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["Location"]


def phase_as(job_url, auth):
    return requests.get(f"{job_url}/phase", auth=auth).text
