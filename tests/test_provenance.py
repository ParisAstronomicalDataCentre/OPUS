#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Tests of the provenance of jobs (IVOA Provenance, /provsap), on a UWS server running in a thread
(live_server fixture), with jobs run by the Local manager:
- chained jobs: test_activity_2 uses the result of test_activity_1
- options of /provsap: DEPTH, DIRECTION, DESCRIPTIONS, CONFIGURATION, AGENTS, MODEL, RESPONSEFORMAT
- internal provenance written by the job script (internal_provenance.json)
"""

import json
import os
import shutil
import xml.etree.ElementTree as ET

import pytest
import requests

from test_jobs import (  # noqa: F401 (server fixture)
    AUTH,
    TEST_JOBS,
    create_job,
    server,
    wait,
)
from uws_server import uws_jdl
from uws_server.settings import settings

INTERNAL_PROVENANCE = {  # PROV-JSON, the activity current_job is the job itself
    "prefix": {"default": "http://example.org/job#", "ext": "http://example.org/"},
    "activity": {"current_job": {}},
    "entity": {
        "ext:software": {"voprov:name": "tool", "voprov:version": "1.2"},
        "ext:calibration": {"prov:label": "calibration file"},
        "ext:log": {"prov:label": "internal log"},
    },
    "agent": {"ext:operator": {"prov:label": "operator"}},
    "used": {
        "_:u1": {"prov:activity": "current_job", "prov:entity": "ext:software", "prov:type": "Software"},
        "_:u2": {"prov:activity": "current_job", "prov:entity": "ext:calibration", "prov:role": "calibration"},
    },
    "wasGeneratedBy": {"_:g1": {"prov:activity": "current_job", "prov:entity": "ext:log", "prov:role": "log"}},
    "wasAssociatedWith": {"_:a1": {"prov:activity": "current_job", "prov:agent": "ext:operator", "prov:role": "operator"}},
}


def base_url(server):  # noqa: F811 (server fixture)
    return server.rsplit(settings.UWS_SERVER_ENDPOINT, 1)[0]


def jobid(job_url):
    return job_url.split("/")[-1]


def provsap(server, *ids, **params):  # noqa: F811 (server fixture)
    """Provenance as PROV-JSON (by default)"""
    params = dict({"RESPONSEFORMAT": "PROV-JSON"}, **params)
    response = requests.get(f"{base_url(server)}/provsap", params=dict(params, ID=list(ids)), auth=AUTH)
    assert response.status_code == 200, response.text
    return response.json() if params["RESPONSEFORMAT"] == "PROV-JSON" else response


def activities(prov):
    return {a.split("/")[-1] for a in prov.get("activity", {})}


def all_records(prov, kind):
    """Records of a kind, also in the bundles"""
    records = dict(prov.get(kind, {}))
    for bundle in prov.get("bundle", {}).values():
        records.update(bundle.get(kind, {}))
    return records


@pytest.fixture(scope="module")
def chain(server):  # noqa: F811 (server fixture)
    """job1 (test_activity_1) generates a result used by job2 (test_activity_2)"""
    job1 = create_job(server, "test_activity_1", text="first")
    assert wait(job1) == "COMPLETED"
    store_url = requests.get(f"{job1}/results/output", auth=AUTH).text
    job2 = create_job(server, "test_activity_2", text="second", input=store_url)
    assert wait(job2) == "COMPLETED"
    entity_id = store_url.split("ID=")[-1]
    return jobid(job1), jobid(job2), entity_id


class TestChain:

    def test_back(self, server, chain):  # noqa: F811 (server fixture)
        job1, job2, entity_id = chain
        # DEPTH=1 (default): the job, and the entity it used
        prov = provsap(server, job2)
        assert activities(prov) == {job2}
        assert f"opus_store:{entity_id}" in prov["entity"]
        used = [u["prov:entity"] for u in prov["used"].values()]
        assert f"opus_store:{entity_id}" in used
        # DEPTH=ALL: also the job that generated the entity
        prov = provsap(server, job2, DEPTH="ALL")
        assert activities(prov) == {job1, job2}
        generations = {(g["prov:entity"], g["prov:activity"].split("/")[-1]) for g in prov["wasGeneratedBy"].values()}
        assert (f"opus_store:{entity_id}", job1) in generations

    def test_forward(self, server, chain):  # noqa: F811 (server fixture)
        job1, job2, entity_id = chain
        prov = provsap(server, job1, DIRECTION="FORWARD", DEPTH="ALL")
        assert activities(prov) == {job1, job2}

    def test_entity(self, server, chain):  # noqa: F811 (server fixture)
        job1, job2, entity_id = chain
        prov = provsap(server, entity_id)
        assert activities(prov) == {job1}
        assert f"opus_store:{entity_id}" in prov["entity"]

    def test_several_ids(self, server, chain):  # noqa: F811 (server fixture)
        job1, job2, entity_id = chain
        assert activities(provsap(server, job1, job2)) == {job1, job2}


class TestOptions:

    def test_agents(self, server, chain):  # noqa: F811 (server fixture)
        job1 = chain[0]
        prov = provsap(server, job1)
        assert f"opus_user:{AUTH[0]}" in prov["agent"]
        assert [a["prov:role"] for a in prov["wasAssociatedWith"].values()] == ["owner"]
        assert "agent" not in provsap(server, job1, AGENTS=0)

    def test_configuration(self, server, chain):  # noqa: F811 (server fixture)
        job1 = chain[0]
        prov = provsap(server, job1)
        parameters = all_records(prov, "parameter")
        [text] = [p for p in parameters.values() if p["prov:label"].startswith("text")]
        assert text["prov:label"] == "text = first"
        assert not all_records(provsap(server, job1, CONFIGURATION=0), "parameter")

    def test_descriptions(self, server, chain):  # noqa: F811 (server fixture)
        job1 = chain[0]
        assert not all_records(provsap(server, job1), "activityDescription")
        prov = provsap(server, job1, DESCRIPTIONS=1)
        [description] = all_records(prov, "activityDescription").values()
        assert description["voprov:version"] == "1"
        assert description["voprov:description"].startswith("Job for tests")
        assert not all_records(prov, "generationDescription")
        # with the descriptions of the results and parameters, and the contact
        prov = provsap(server, job1, DESCRIPTIONS=2)
        assert "opus_jdl:test_activity_1#output" in all_records(prov, "generationDescription")
        assert "opus_jdl:test_activity_1#text" in all_records(prov, "parameterDescription")
        assert "opus-admin" in prov["agent"] or "opus_user:opus-admin" in prov["agent"]

    def test_w3c(self, server, chain):  # noqa: F811 (server fixture)
        prov = provsap(server, chain[0], MODEL="W3C", DESCRIPTIONS=2)
        assert activities(prov) == {chain[0]}
        assert not all_records(prov, "activityDescription")


class TestFormats:

    def test_xml(self, server, chain):  # noqa: F811 (server fixture)
        response = provsap(server, chain[0], RESPONSEFORMAT="PROV-XML")
        assert response.headers["Content-Type"].startswith("text/xml")
        assert f'filename="provsap_{chain[0]}.xml"' in response.headers["Content-Disposition"]
        assert ET.fromstring(response.content).tag.endswith("}document")

    @pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz (dot) is not installed")
    def test_images(self, server, chain):  # noqa: F811 (server fixture)
        assert "<svg" in provsap(server, chain[0], RESPONSEFORMAT="PROV-SVG").text
        response = provsap(server, chain[0], RESPONSEFORMAT="PROV-PNG", ATTRIBUTES=0, GD="BT")
        assert response.content.startswith(b"\x89PNG")

    def test_errors(self, server):  # noqa: F811 (server fixture)
        url = f"{base_url(server)}/provsap"
        assert requests.get(url, params={"ID": "x", "RESPONSEFORMAT": "PDF"}, auth=AUTH).status_code in (400, 404)
        assert requests.get(url, auth=AUTH).status_code == 400  # no ID
        assert requests.get(url, params={"ID": "unknown"}, auth=AUTH).status_code == 404


class TestInternalProvenance:

    @pytest.fixture(scope="class")
    def job(self, server):  # noqa: F811 (server fixture)
        """Job writing an internal provenance file"""
        with open(os.path.join(TEST_JOBS, "test_activity_1_vot.xml")) as f:
            vot = f.read().replace("test_activity_1", "test_internal_prov")
        with open(f"{settings.JDL_PATH}/votable/test_internal_prov_vot.xml", "w") as f:
            f.write(vot)
        script = f"echo $text > $output\ncat > internal_provenance.json << 'EOF'\n{json.dumps(INTERNAL_PROVENANCE)}\nEOF\n"
        getattr(uws_jdl, settings.JDL)().save_script("test_internal_prov", script)
        job_url = create_job(server, "test_internal_prov", text="internal")
        assert wait(job_url) == "COMPLETED"
        return jobid(job_url)

    def test_internal_provenance(self, server, job):  # noqa: F811 (server fixture)
        assert os.path.isfile(os.path.join(settings.JOBDATA_PATH, job, "internal_provenance.json"))
        prov = provsap(server, job, DESCRIPTIONS=1)
        assert "ext:calibration" in prov["entity"]
        roles = {u["prov:entity"]: u.get("prov:role") for u in prov["used"].values()}
        assert roles["ext:calibration"] == "calibration"
        assert "ext:log" in [g["prov:entity"] for g in prov["wasGeneratedBy"].values()]
        assert "ext:operator" in [a["prov:agent"] for a in prov["wasAssociatedWith"].values()]
        # the software is a dependency of the job description
        assert prov["entity"]["ext:software"]["prov:label"] == "tool 1.2"
        [description] = all_records(prov, "activityDescription")
        influences = [(i["prov:influencee"], i["prov:influencer"]) for i in prov["wasInfluencedBy"].values()]
        assert (description, "ext:software") in influences

    def test_internal_provenance_without_descriptions(self, server, job):  # noqa: F811 (server fixture)
        prov = provsap(server, job)
        # the software is then used by the job
        assert {"ext:calibration", "ext:software"} <= {u["prov:entity"] for u in prov["used"].values()}
