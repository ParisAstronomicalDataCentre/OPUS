#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Tests running real jobs with the Local manager, on a UWS server running in a thread
(live_server fixture): the jobs report their phase to the server (job_event), as in production

The job definitions test_activity_1 and test_activity_2 of test_jobs/ are used, with test scripts:
- test_activity_1 writes the parameter text in the result output, fails if text starts with
  "fail" (exit 3, or a command failing for "fail-command"), and waits if text starts with "slow"
- test_activity_2 writes the input file and the parameter text in the result output
"""

import html
import json
import os
import shutil
import time
import xml.etree.ElementTree as ET

import psutil
import pytest
import requests

from uws_server import storage, uws_jdl
from uws_server.settings import settings

TEST_JOBS = os.path.join(os.path.dirname(__file__), os.pardir, "test_jobs")
SCRIPTS = {
    "test_activity_1": """case "$text" in
    slow*) sleep 30 ;;
    fail-command*) false ;;
    fail*) echo "failed on purpose" >&2; exit 3 ;;
esac
echo $text > $output
""",
    "test_activity_2": """cat $input > $output
echo $text >> $output
""",
}
AUTH = ("jobs@example.org", "jobs-token")
ADMIN = (settings.ADMIN_NAME, settings.ADMIN_TOKEN.get_secret_value())
UWS = "{{http://www.ivoa.net/xml/UWS/v1.0}}{}"
TIMEOUT = 30  # in seconds


@pytest.fixture(scope="module")
def server(live_server):
    """UWS server running the jobs with the Local manager"""
    manager = settings.MANAGER
    settings.MANAGER = "Local"
    jdl = getattr(uws_jdl, settings.JDL)()
    for jobname, script in SCRIPTS.items():
        shutil.copy(os.path.join(TEST_JOBS, f"{jobname}_vot.xml"), f"{settings.JDL_PATH}/votable/")
        jdl.save_script(jobname, script)
    yield f"{live_server}{settings.UWS_SERVER_ENDPOINT}"
    settings.MANAGER = manager


def create_job(server, jobname, run=True, **params):
    """Create a job, return its URL"""
    data = dict(params, PHASE="RUN") if run else params
    response = requests.post(f"{server}/{jobname}", data=data, auth=AUTH, allow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["Location"]


def phase(job_url):
    return requests.get(f"{job_url}/phase", auth=AUTH).text


def wait(job_url, phases=("COMPLETED", "ERROR", "ABORTED")):
    """Wait until the job reaches one of the phases, return its phase"""
    start = time.time()
    while time.time() - start < TIMEOUT:
        p = phase(job_url)
        if p in phases:
            return p
        time.sleep(0.1)
    raise AssertionError(f"Job {job_url} still {p} after {TIMEOUT}s")


def wait_saved(job_url):
    """Wait until a completed job is saved with its provenance files (saved after the phase COMPLETED), before
    changing it in the database (else the change could be overwritten)"""
    start = time.time()
    while "provjson" not in requests.get(f"{job_url}/results", auth=AUTH).text:
        assert time.time() - start < TIMEOUT, f"Job {job_url} not saved with its provenance"
        time.sleep(0.1)


def process_id(job_url):
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    with job_storage.get_session() as session:
        return int(session.query(job_storage.Job).filter_by(jobid=job_url.split("/")[-1]).one().process_id)


def group_processes(pgid):
    """Processes still running in the process group of a job (the job and its child processes)"""
    time.sleep(0.2)
    running = []
    for p in psutil.process_iter(["pid", "status"]):
        try:
            if os.getpgid(p.pid) == pgid and p.info["status"] != psutil.STATUS_ZOMBIE:
                running.append(p.pid)
        except (ProcessLookupError, PermissionError):
            pass
    return running


def result(job_url, name="output"):
    """Content of a result of the job"""
    store_url = requests.get(f"{job_url}/results/{name}", auth=AUTH).text
    return requests.get(store_url, auth=AUTH).text


def job_attributes(job_url):
    root = ET.fromstring(requests.get(job_url, auth=AUTH).text)
    return {child.tag.split("}")[1]: child.text for child in root}


class TestRunJobs:

    def test_completed(self, server):
        job_url = create_job(server, "test_activity_1", text="hello")
        assert wait(job_url) == "COMPLETED"
        assert result(job_url) == "hello\n"
        attributes = job_attributes(job_url)
        assert attributes["phase"] == "COMPLETED"
        assert attributes["startTime"] and attributes["endTime"]
        assert requests.get(f"{job_url}/stdout", auth=AUTH).status_code == 200
        # batch script run with the shell of the settings (OPUS_BATCH_SHELL, no login shell in the tests)
        with open(f"{settings.JOBDATA_PATH}/{job_url.split('/')[-1]}/batch.sh") as f:
            assert f.readline().strip() == f"#!{settings.BATCH_SHELL}" == "#!/bin/bash"

    def test_chained_jobs(self, server):
        job1 = create_job(server, "test_activity_1", text="first")
        assert wait(job1) == "COMPLETED"
        store_url = requests.get(f"{job1}/results/output", auth=AUTH).text
        job2 = create_job(server, "test_activity_2", text="second", input=store_url)
        assert wait(job2) == "COMPLETED"
        assert result(job2) == "first\nsecond\n"

    def test_error(self, server):
        job_url = create_job(server, "test_activity_1", text="fail")
        assert wait(job_url) == "ERROR"
        assert "failed on purpose" in requests.get(f"{job_url}/stderr", auth=AUTH).text
        assert "exited with code 3" in requests.get(f"{job_url}/error", auth=AUTH).text

    def test_error_command(self, server):
        job_url = create_job(server, "test_activity_1", text="fail-command")
        assert wait(job_url) == "ERROR"
        assert "false" in requests.get(f"{job_url}/error", auth=AUTH).text

    def test_abort(self, server):
        job_url = create_job(server, "test_activity_1", text="slow")
        assert wait(job_url, phases=("EXECUTING",)) == "EXECUTING"
        pgid = process_id(job_url)
        assert group_processes(pgid)  # batch.sh and sleep
        requests.post(f"{job_url}/phase", data={"PHASE": "ABORT"}, auth=AUTH)
        assert wait(job_url) == "ABORTED"
        assert group_processes(pgid) == []  # the child processes are stopped too

    def test_pending_job(self, server):
        job_url = create_job(server, "test_activity_1", run=False, text="before")
        assert phase(job_url) == "PENDING"
        requests.post(f"{job_url}/parameters/text", data={"VALUE": "after"}, auth=AUTH)
        requests.post(f"{job_url}/phase", data={"PHASE": "RUN"}, auth=AUTH)
        assert wait(job_url) == "COMPLETED"
        assert result(job_url) == "after\n"

    def test_delete(self, server):
        job_url = create_job(server, "test_activity_1", text="deleted")
        assert wait(job_url) == "COMPLETED"
        jobid = job_url.split("/")[-1]
        assert requests.delete(job_url, auth=AUTH).status_code in (200, 303)
        assert requests.get(job_url, auth=AUTH).status_code == 404
        assert not os.path.exists(f"{settings.JOBDATA_PATH}/{jobid}")


@pytest.fixture(scope="module")
def provenance_job(server):
    """Completed job, for the provenance tests"""
    job_url = create_job(server, "test_activity_1", text="provenance")
    assert wait(job_url) == "COMPLETED"
    wait_saved(job_url)  # provenance files added after the phase COMPLETED
    return job_url


class TestInvalidInput:
    """Input of a job missing or not found: error 400 with the reason, and no job left"""

    def job_ids(self, server):  # noqa: F811 (server fixture)
        root = ET.fromstring(requests.get(f"{server}/test_activity_2", auth=AUTH).text)
        return {job.get("id") or job.find("{*}jobId").text for job in root}

    @pytest.mark.parametrize(
        "params, reason",
        [
            ({}, "'input.txt' is not an identifier of the entity store, nor a URL"),  # default value of the input
            ({"input": ""}, "Input 'input' is required"),
            ({"input": "http://localhost:1/nothing"}, "cannot get http://localhost:1/nothing (ConnectionError)"),
            ({"input": "__base__/store?ID=unknown"}, "Input 'input': result unknown not found in the entity store"),
            ({"input": "__base__/nothing"}, "/nothing (HTTP 4"),  # HTTP error
        ],
    )
    def test_invalid_input(self, server, params, reason):  # noqa: F811 (server fixture)
        base = server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]
        params = {k: v.replace("__base__", base) for k, v in params.items()}
        before = self.job_ids(server)
        response = requests.post(f"{server}/test_activity_2", data=dict(params, text="x"), auth=AUTH, allow_redirects=False)
        assert response.status_code == 400, response.text
        assert reason in html.unescape(response.text)
        assert self.job_ids(server) == before  # the job is not kept


class TestProvenance:

    def test_json(self, provenance_job):
        prov = json.loads(requests.get(f"{provenance_job}/provjson", auth=AUTH).text)
        assert prov["activity"] and prov["entity"] and prov["wasGeneratedBy"]

    def test_xml(self, provenance_job):
        response = requests.get(f"{provenance_job}/provxml", auth=AUTH)
        assert response.status_code == 200
        assert ET.fromstring(response.text).tag.endswith("document")

    @pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz (dot) is not installed")
    def test_svg(self, provenance_job, server):
        response = requests.get(f"{provenance_job}/provsvg", auth=AUTH)
        assert response.status_code == 200 and "<svg" in response.text
        jobid = provenance_job.split("/")[-1]
        base = server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]
        graph = requests.get(f"{base}/provsap", params={"ID": jobid}, auth=AUTH)
        assert graph.status_code == 200


class TestMaintenance:

    def archive(self, server, text):
        """Completed job, archived by the maintenance after its destruction date"""
        job_url = create_job(server, "test_activity_1", text=text)
        assert wait(job_url) == "COMPLETED"
        wait_saved(job_url)
        jobid = job_url.split("/")[-1]
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        with job_storage.get_session() as session:
            session.query(job_storage.Job).filter_by(jobid=jobid).update({"destruction_time": "2020-01-01T00:00:00"})
            session.commit()
        base = server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]
        report = requests.get(f"{base}/handler/maintenance/test_activity_1").text
        assert f"{jobid}" in report and "archived" in report
        return job_url

    def test_archive(self, server):
        assert phase(self.archive(server, "archived")) == "ARCHIVED"

    def expired_job(self, server, text, **attributes):
        """Completed job, with a destruction time passed (and other attributes changed in the database)"""
        job_url = create_job(server, "test_activity_1", text=text)
        assert wait(job_url) == "COMPLETED"
        wait_saved(job_url)
        return self.expire(job_url, **attributes)

    def expire(self, job_url, **attributes):
        """Destruction time passed (and other attributes changed in the database)"""
        jobid = job_url.split("/")[-1]
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        with job_storage.get_session() as session:
            values = dict({"destruction_time": "2020-01-01T00:00:00"}, **attributes)
            session.query(job_storage.Job).filter_by(jobid=jobid).update(values)
            session.commit()
        return job_url, jobid

    def job_report(self, server, jobid, method="GET"):
        base = server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]
        response = requests.request(method, f"{base}/maintenance", params={"JOBNAME": "test_activity_1"}, auth=ADMIN)
        assert response.status_code == 200, response.text
        report = response.json()
        [record] = [r for r in report["jobs"] if r["jobid"] == jobid]
        return report, record

    def test_check_then_apply(self, server):
        job_url, jobid = self.expired_job(server, "check then apply")
        # dry run: reported, nothing changed
        report, record = self.job_report(server, jobid)
        assert not report["apply"] and report["summary"]["to_archive"] >= 1
        assert "to_archive" in record["categories"] and record["actions"] == ["to archive (destruction time passed)"]
        assert "end_time > destruction_time" in record["issues"]  # destruction time set in the past for the test
        assert phase(job_url) == "COMPLETED"
        # apply
        report, record = self.job_report(server, jobid, method="POST")
        assert report["apply"] and record["actions"] == ["archived (destruction time passed)"]
        assert phase(job_url) == "ARCHIVED"
        # already archived
        report, record = self.job_report(server, jobid)
        assert "archived" in record["categories"] and "to_archive" not in record["categories"]
        assert not record["actions"]

    def test_delete_pending(self, server):
        """An expired job that cannot be archived (not completed, aborted or in error) is deleted"""
        job_url = create_job(server, "test_activity_1", run=False, text="expired pending")
        job_url, jobid = self.expire(job_url)
        report, record = self.job_report(server, jobid)
        assert "to_delete" in record["categories"]
        assert record["actions"] == ["to delete (destruction time passed, phase PENDING)"]
        assert phase(job_url) == "PENDING"  # dry run
        report, record = self.job_report(server, jobid, method="POST")
        assert record["actions"] == ["deleted (destruction time passed, phase PENDING)"]
        assert requests.get(job_url, auth=AUTH).status_code == 404

    def test_delete_executing(self, server):
        """An expired job still running is stopped and deleted"""
        job_url = create_job(server, "test_activity_1", text="slow expired")
        assert wait(job_url, phases=("EXECUTING",)) == "EXECUTING"
        pgid = process_id(job_url)
        job_url, jobid = self.expire(job_url)
        report, record = self.job_report(server, jobid, method="POST")
        assert record["actions"] == ["deleted (destruction time passed, phase EXECUTING)"]
        assert group_processes(pgid) == []
        assert requests.get(job_url, auth=AUTH).status_code == 404
        assert not os.path.exists(f"{settings.JOBDATA_PATH}/{jobid}")

    def test_delete_without_archived_phase(self, server, monkeypatch):
        """Without the ARCHIVED phase, the expired jobs are deleted (with their results)"""
        monkeypatch.setattr(settings, "USE_ARCHIVED_PHASE", False)
        job_url, jobid = self.expired_job(server, "expired, no archive")
        report, record = self.job_report(server, jobid, method="POST")
        assert "to_delete" in record["categories"] and "to_archive" not in record["categories"]
        assert requests.get(job_url, auth=AUTH).status_code == 404
        assert not os.path.exists(f"{settings.RESULTS_PATH}/{jobid}")

    def test_dates(self, server):
        job_url, jobid = self.expired_job(server, "dates", destruction_time="2099-01-01T00:00:00",
                                          start_time="2000-01-01T00:00:00")
        report, record = self.job_report(server, jobid)
        assert record["categories"] == ["dates"] and record["issues"] == ["creation_time > start_time"], record

    def test_admin_only(self, server):
        base = server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]
        assert requests.get(f"{base}/maintenance", auth=AUTH).status_code == 403
        assert requests.post(f"{base}/maintenance", auth=AUTH).status_code == 403

    def test_archive_deletes_results(self, server):
        """The result files of an archived job are deleted, its description, results (provenance), logs and provenance
        files are kept"""
        job_url = self.archive(server, "results deleted")
        jobid = job_url.split("/")[-1]
        assert not os.path.exists(f"{settings.RESULTS_PATH}/{jobid}")
        # the result is kept (provenance), its file is no longer available
        response = requests.get(f"{job_url}/results/output", auth=AUTH)
        assert response.status_code == 200
        download = requests.get(response.text, auth=AUTH)
        assert download.status_code == 404
        assert f"job {jobid} is archived (its result files were deleted)" in download.text
        # kept: description, parameters, logs and provenance
        assert job_attributes(job_url)["phase"] == "ARCHIVED"
        assert requests.get(f"{job_url}/parameters/text", auth=AUTH).text == "results deleted"
        assert requests.get(f"{job_url}/stdout", auth=AUTH).status_code == 200
        assert requests.get(f"{job_url}/provjson", auth=AUTH).status_code == 200
        # the entity of the result is kept, its file is no longer available
        job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
        with job_storage.get_session() as session:
            [entity_id] = [e.entity_id for e in session.query(job_storage.Entity).filter_by(jobid=jobid)]
        base = server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]
        assert requests.get(f"{base}/store", params={"ID": entity_id}, auth=AUTH).status_code == 404
