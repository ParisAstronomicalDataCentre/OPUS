#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Tests of the job definition workflow, on a UWS server running in a thread (live_server fixture),
as used by the Job Definition page of the client:
- a user submits a job definition (form or imported file), saved in tmp/
- the user sends a validation request to the admin (email, intercepted here)
- the admin validates the job definition (the previous version is kept in saved/),
  the job can then be run
- the admin deletes the job definition (kept in saved/ as _DELETED)
"""

import glob
import os
import re

import pytest
import requests

from test_jobs import (  # noqa: F401 (server fixture)
    AUTH,
    create_job,
    result,
    server,
    wait,
)
from uws_server import uws_server
from uws_server.settings import settings

ADMIN = (settings.ADMIN_NAME, settings.ADMIN_TOKEN.get_secret_value())
TEST_JOBS = os.path.join(os.path.dirname(__file__), os.pardir, "test_jobs")


def base_url(server):  # noqa: F811 (server fixture)
    return server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]


def definition(jobname, version="1", script="echo $text > $output\n", used=False):
    """Form of the Job Definition page"""
    form = {
        "name": jobname,
        "annotation": f"Test job {jobname}",
        "version": version,
        "type": "test",
        "executionDuration": "60",
        "script": script,
        "param_name_1": "text",
        "param_datatype_1": "xs:string",
        "param_default_1": "Hello",
        "param_required_1": "on",
        "param_annotation_1": "Input text",
        "param_name_2": "mode",
        "param_datatype_2": "xs:string",
        "param_default_2": "fast",
        "param_options_2": "fast,slow",
        "param_attributes_2": "arraysize=* unit=none",
        "generated_name_1": "output",
        "generated_contenttype_1": "text/plain",
        "generated_default_1": "output.txt",
        "generated_annotation_1": "Output file",
    }
    if used:
        form.update(
            {
                "used_name_1": "input",
                "used_contenttype_1": "text/plain",
                "used_multiplicity_1": "1",
                "used_isfile_1": "File",
                "used_annotation_1": "Input file",
            }
        )
    return form


def submit(server, jobname, **kwargs):  # noqa: F811 (server fixture)
    response = requests.post(f"{base_url(server)}/jdl", data=definition(jobname, **kwargs), auth=AUTH)
    assert response.status_code == 200, response.text
    assert response.json() == {"jobname": jobname}


def validate(server, jobname, auth=ADMIN):  # noqa: F811 (server fixture)
    return requests.post(f"{base_url(server)}/jdl/tmp/{jobname}/validate", auth=auth)


def jdl_json(server, jobname):  # noqa: F811 (server fixture)
    return requests.get(f"{base_url(server)}/jdl/{jobname}/json", auth=AUTH)


def jobnames(server):  # noqa: F811 (server fixture)
    return requests.get(f"{base_url(server)}/jdl", auth=AUTH).json()["jobnames"]


def saved(pattern):
    """Files kept in the saved/ directories (job definitions and scripts)"""
    return sorted(
        os.path.basename(f)
        for d in (f"{settings.JDL_PATH}/votable/saved", f"{settings.SCRIPTS_PATH}/saved")
        for f in glob.glob(f"{d}/{pattern}")
    )


class TestSubmit:

    def test_form(self, server):  # noqa: F811 (server fixture)
        submit(server, "def_form", used=True)
        content = jdl_json(server, "tmp/def_form").json()
        assert content["name"] == "def_form"
        assert content["annotation"] == "Test job def_form"
        assert content["version"] == "1"
        assert content["contact_name"] == AUTH[0]  # the user submitting the form, by default
        assert content["executionDuration"] == "60"
        text = content["parameters"]["text"]
        assert (text["datatype"], text["default"], text["annotation"]) == ("xs:string", "Hello", "Input text")
        assert text["required"] in (True, "true")
        mode = content["parameters"]["mode"]
        assert mode["options"] == "fast,slow" and mode["unit"] == "none"
        assert content["used"]["input"]["url"] == "file://$ID"
        assert content["used"]["input"]["content_type"] == "text/plain"
        output = content["generated"]["output"]
        assert (output["content_type"], output["default"]) == ("text/plain", "output.txt")
        script = requests.get(f"{base_url(server)}/jdl/tmp/def_form/script", auth=AUTH)
        assert script.text == "echo $text > $output\n"
        # not a validated job definition
        assert "def_form" not in jobnames(server)

    def test_form_without_name(self, server):  # noqa: F811 (server fixture)
        response = requests.post(f"{base_url(server)}/jdl", data=definition(""), auth=AUTH)
        assert response.status_code == 500

    def test_import(self, server, tmp_path):  # noqa: F811 (server fixture)
        with open(os.path.join(TEST_JOBS, "test_activity_1_vot.xml")) as f:
            vot = f.read().replace("test_activity_1", "def_import")
        # the name of the job definition is taken from the file name...
        path = tmp_path / "def_import_vot.xml"
        path.write_text(vot)
        with open(path, "rb") as f:
            response = requests.post(f"{base_url(server)}/jdl/import_jdl", files={"jdl_file": f}, auth=AUTH)
        assert response.json() == {"jobname": "def_import"}
        content = jdl_json(server, "tmp/def_import").json()
        assert content["name"] == "def_import" and "text" in content["parameters"]
        # ... or from its content, if they differ
        path = tmp_path / "other_name_vot.xml"
        path.write_text(vot)
        with open(path, "rb") as f:
            response = requests.post(f"{base_url(server)}/jdl/import_jdl", files={"jdl_file": f}, auth=AUTH)
        assert response.json() == {"jobname": "def_import"}
        assert not os.path.exists(f"{settings.JDL_PATH}/votable/tmp/other_name_vot.xml")

    def test_unknown(self, server):  # noqa: F811 (server fixture)
        assert jdl_json(server, "tmp/def_unknown").status_code == 404
        assert requests.get(f"{base_url(server)}/jdl/def_unknown", auth=AUTH).status_code == 404


class TestValidation:

    @pytest.fixture
    def mails(self, monkeypatch):
        """Emails sent by the server (not sent)"""
        sent = []
        monkeypatch.setattr(uws_server, "send_mail", lambda *args: sent.append(args))
        return sent

    def test_validation_request(self, server, mails):  # noqa: F811 (server fixture)
        submit(server, "def_request")
        response = requests.post(f"{base_url(server)}/jdl/tmp/def_request/validation_request", auth=AUTH)
        assert response.status_code == 200
        [(send_to, subject, text)] = mails
        assert send_to == settings.ADMIN_EMAIL
        assert "def_request" in subject
        assert "/jdl/tmp/def_request/json" in text and AUTH[0] in text
        # no job definition submitted
        response = requests.post(f"{base_url(server)}/jdl/tmp/def_unknown/validation_request", auth=AUTH)
        assert response.status_code == 500 and len(mails) == 1

    def test_validate_admin_only(self, server):  # noqa: F811 (server fixture)
        submit(server, "def_admin_only")
        assert validate(server, "def_admin_only", auth=AUTH).status_code == 403
        assert "def_admin_only" not in jobnames(server)

    def test_validate_unknown(self, server):  # noqa: F811 (server fixture)
        assert validate(server, "def_unknown").status_code == 500

    def test_validate_and_run(self, server):  # noqa: F811 (server fixture)
        submit(server, "def_run")
        assert validate(server, "def_run").status_code == 200
        assert "def_run" in jobnames(server)
        assert jdl_json(server, "def_run").json()["version"] == "1"
        job_url = create_job(server, "def_run", text="version 1")
        assert wait(job_url) == "COMPLETED"
        assert result(job_url) == "version 1\n"
        # new version: the previous version is kept in saved/
        submit(server, "def_run", version="2", script='echo "v2 $text" > $output\n')
        assert validate(server, "def_run").status_code == 200
        assert jdl_json(server, "def_run").json()["version"] == "2"
        files = saved("def_run_v1_*")
        assert len(files) == 2
        assert re.fullmatch(r"def_run_v1_[\dT:-]+\.sh", files[0])
        assert re.fullmatch(r"def_run_v1_[\dT:-]+_vot\.xml", files[1])
        job_url = create_job(server, "def_run", text="version 2")
        assert wait(job_url) == "COMPLETED"
        assert result(job_url) == "v2 version 2\n"

    def test_download(self, server):  # noqa: F811 (server fixture)
        submit(server, "def_download")
        validate(server, "def_download")
        response = requests.get(f"{base_url(server)}/jdl/def_download", auth=AUTH)
        assert response.status_code == 200
        assert 'filename="def_download_vot.xml"' in response.headers["Content-Disposition"]
        assert response.text.startswith("<VOTABLE") and 'name="def_download"' in response.text


class TestDelete:

    def test_delete(self, server):  # noqa: F811 (server fixture)
        submit(server, "def_delete", version="3")
        validate(server, "def_delete")
        # admin only
        assert requests.delete(f"{base_url(server)}/jdl/def_delete", auth=AUTH).status_code == 403
        assert "def_delete" in jobnames(server)
        response = requests.delete(f"{base_url(server)}/jdl/def_delete", auth=ADMIN)
        assert response.status_code == 200
        assert "def_delete" not in jobnames(server)
        assert jdl_json(server, "def_delete").status_code == 404
        files = saved("def_delete_v3_*_DELETED*")
        assert len(files) == 2  # job definition and script
        # already deleted
        assert requests.delete(f"{base_url(server)}/jdl/def_delete", auth=ADMIN).status_code == 404
