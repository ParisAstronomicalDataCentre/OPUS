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

import json
import os
import shutil
import time
import xml.etree.ElementTree as ET

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
        time.sleep(0.3)
    raise AssertionError(f"Job {job_url} still {p} after {TIMEOUT}s")


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
        requests.post(f"{job_url}/phase", data={"PHASE": "ABORT"}, auth=AUTH)
        assert wait(job_url) == "ABORTED"

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
    return job_url


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

    @pytest.mark.xfail(reason="deletion of the results of the archived jobs not implemented yet", strict=True)
    def test_archive_deletes_results(self, server):
        job_url = self.archive(server, "results deleted")
        assert requests.get(f"{job_url}/results/output", auth=AUTH).status_code == 404
