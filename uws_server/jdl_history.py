#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
History of the job definitions (Job Definitions page of the client, admin only)

Versions of a job definition, from the files:
- pending: submitted in tmp/ (form or import), removed from tmp/ when validated or rejected (a file of tmp/
  identical to the current version, e.g. left by a previous version of OPUS, is removed: nothing to validate)
- current: validated job definition
- saved: previous versions, kept in saved/ when a new version is validated or when the job definition is deleted
  (<jobname>_v<version>_<date>[_DELETED], date of the saved file, i.e. when this version was validated)

Events (who did what), logged in <JDL_PATH>/history/<jobname>.jsonl: submitted, validation_requested, validated,
rejected, deleted, restored (a saved version validated again). The job definitions validated before this log have no events, only their versions.
"""

import datetime as dt
import difflib
import glob
import json
import os
import re
import shutil

from . import uws_jdl
from .settings import DT_FMT, logger, settings

EVENTS = ["submitted", "validation_requested", "validated", "rejected", "deleted", "restored"]
JOBNAME_RE = re.compile(r"^[\w.-]+$")


def _jdl():
    return getattr(uws_jdl, settings.JDL)()


def history_dir():
    return os.path.join(settings.JDL_PATH, "history")


def check_jobname(jobname):
    if not JOBNAME_RE.match(jobname or ""):
        raise ValueError(f"Invalid job name: {jobname}")


def _mtime(path):
    return dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime(DT_FMT)


# ----------
# Events


def log_event(jobname, event, user, **info):
    """Add an event to the history of the job definition"""
    check_jobname(jobname)
    os.makedirs(history_dir(), exist_ok=True)
    record = {"date": dt.datetime.now().strftime(DT_FMT), "event": event, "user": user, **info}
    with open(os.path.join(history_dir(), f"{jobname}.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")
    logger.info(f"Job definition {jobname}: {event} by {user} {info if info else ''}")


def events(jobname):
    """Events of the job definition, oldest first"""
    check_jobname(jobname)
    path = os.path.join(history_dir(), f"{jobname}.jsonl")
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


# ----------
# Versions


def saved_stem(jobname, version, date, deleted=False):
    """Name of a saved version (without extension), date as in the file names of previous versions"""
    return f"{jobname}_v{version}_{date}" + ("_DELETED" if deleted else "")


def _files(jobname, vid):
    """JDL file and script file of a version: pending, current, or the name of a saved version"""
    jdl = _jdl()
    if vid == "pending":
        return jdl._get_filename(f"tmp/{jobname}"), f"{jdl.scripts_path}/tmp/{jobname}.sh"
    if vid == "current":
        return jdl._get_filename(jobname), f"{jdl.scripts_path}/{jobname}.sh"
    if vid in {v["id"] for v in _saved_versions(jobname)}:
        return jdl._get_filename(f"saved/{vid}"), f"{jdl.scripts_path}/saved/{vid}.sh"
    raise FileNotFoundError(f"Version {vid} not found for job definition {jobname}")


def _saved_versions(jobname):
    jdl = _jdl()
    pattern = re.compile(
        re.escape(jobname) + r"_v(?P<version>[^_]*)_(?P<date>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?P<deleted>_DELETED)?$"
    )
    versions = []
    for path in glob.glob(f"{jdl.jdl_path}/saved/{glob.escape(jobname)}_v*{jdl.extension}"):
        stem = os.path.basename(path)[: -len(jdl.extension)]
        m = pattern.match(stem)
        if m:
            versions.append({
                "id": stem,
                "kind": "deleted" if m["deleted"] else "saved",
                "version": m["version"],
                "date": m["date"],
            })
    return versions


def _read(jobname, vid):
    """Content of a version: (definition without the script, script)"""
    jdl_file, script_file = _files(jobname, vid)
    if not os.path.isfile(jdl_file):
        raise FileNotFoundError(f"Version {vid} not found for job definition {jobname}")
    jdl = _jdl()
    name = os.path.relpath(jdl_file, jdl.jdl_path)[: -len(jdl.extension)]
    jdl.read(name)
    content = dict(jdl.content)
    script = content.pop("script", "") or ""
    if os.path.isfile(script_file):
        with open(script_file) as f:
            script = f.read()
    return content, script


def _pending_status(jobname):
    """Status of the file of tmp/: new, changed, or None (no file, or identical to the current version: removed)"""
    jdl = _jdl()
    jdl_file, script_file = _files(jobname, "pending")
    if not os.path.isfile(jdl_file):
        return None
    if not os.path.isfile(jdl._get_filename(jobname)):
        return "new"
    if _read(jobname, "pending") != _read(jobname, "current"):
        return "changed"
    # identical to the current version: nothing to validate (e.g. kept in tmp/ by a previous version of OPUS)
    for path in [jdl_file, script_file]:
        if os.path.isfile(path):
            os.remove(path)
    logger.info(f"Job definition tmp/{jobname} removed: identical to the validated version")
    return None


def remove_identical_pending():
    """Remove the job definitions of tmp/ identical to the validated version (done at the start of the server)"""
    jdl = _jdl()
    for path in glob.glob(f"{jdl.jdl_path}/tmp/*{jdl.extension}"):
        jobname = os.path.basename(path)[: -len(jdl.extension)]
        if JOBNAME_RE.match(jobname):
            try:
                _pending_status(jobname)
            except Exception as e:
                logger.warning(f"Cannot check the job definition tmp/{jobname}: {e}")


def versions(jobname):
    """Versions of the job definition, most recent first"""
    check_jobname(jobname)
    result = []
    for vid, kind in [("pending", "pending"), ("current", "current")]:
        jdl_file, _ = _files(jobname, vid)
        if vid == "pending" and not _pending_status(jobname):
            continue
        if os.path.isfile(jdl_file):
            try:
                version = _read(jobname, vid)[0].get("version", "")
            except Exception as e:
                logger.warning(f"Cannot read version {vid} of {jobname}: {e}")
                version = ""
            result.append({"id": vid, "kind": kind, "version": version, "date": _mtime(jdl_file)})
    saved = sorted(_saved_versions(jobname), key=lambda v: v["date"], reverse=True)
    return result + saved


def pending():
    """Job definitions submitted in tmp/ and not validated: new, or different from the current version"""
    jdl = _jdl()
    result = []
    for path in sorted(glob.glob(f"{jdl.jdl_path}/tmp/*{jdl.extension}")):
        jobname = os.path.basename(path)[: -len(jdl.extension)]
        if not JOBNAME_RE.match(jobname):
            continue
        try:
            status = _pending_status(jobname)
            if not status:
                continue  # identical to the current version (removed)
            pending_content = _read(jobname, "pending")
        except Exception as e:
            logger.warning(f"Cannot read pending job definition {jobname}: {e}")
            continue
        # last submission, and validation request after it
        submitted, requested = {}, False
        for event in events(jobname):
            if event["event"] == "submitted":
                submitted, requested = event, False
            elif event["event"] == "validation_requested":
                requested = True
        result.append({
            "jobname": jobname,
            "status": status,
            "version": pending_content[0].get("version", ""),
            "date": _mtime(path),
            "submitted_by": submitted.get("user"),
            "validation_requested": requested,
        })
    return result


def inactive():
    """Job definitions found in the history (saved versions, events) without validated version: deleted, or never
    validated (e.g. rejected)"""
    jdl = _jdl()
    stem_re = re.compile(r"^(?P<jobname>.+)_v[^_]*_\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(_DELETED)?$")
    jobnames = set()
    for path in glob.glob(f"{jdl.jdl_path}/saved/*{jdl.extension}"):
        m = stem_re.match(os.path.basename(path)[: -len(jdl.extension)])
        if m:
            jobnames.add(m["jobname"])
    jobnames |= {os.path.basename(p)[: -len(".jsonl")] for p in glob.glob(f"{history_dir()}/*.jsonl")}
    result = []
    for jobname in sorted(jobnames):
        if not JOBNAME_RE.match(jobname) or os.path.isfile(jdl._get_filename(jobname)):
            continue
        saved = sorted(_saved_versions(jobname), key=lambda v: v["date"], reverse=True)
        job_events = events(jobname)
        deleted = next((e for e in reversed(job_events) if e["event"] == "deleted"), None)
        last = job_events[-1] if job_events else None
        result.append({
            "jobname": jobname,
            "status": "deleted" if saved else "never validated",
            "last_version": saved[0] if saved else None,  # version to restore
            "date": (deleted or last or {}).get("date") or (saved[0]["date"] if saved else None),
            "user": (deleted or last or {}).get("user"),
            "last_event": last["event"] if last else None,
        })
    return result


def restore(jobname, vid):
    """Validate again a saved version: the current version (if any) is kept in saved/, the saved version is copied
    as the current version (and kept in saved/). Returns (version, name of the saved current version or None)"""
    check_jobname(jobname)
    if vid in ("pending", "current"):
        raise FileNotFoundError(f"Version {vid} cannot be restored, only a saved version")
    jdl_file, script_file = _files(jobname, vid)  # FileNotFoundError if not a saved version
    version = _read(jobname, vid)[0].get("version", "")
    jdl = _jdl()
    current_jdl, current_script = _files(jobname, "current")
    saved = None
    if os.path.isfile(current_jdl):
        current_version = _read(jobname, "current")[0].get("version", "")
        saved = saved_stem(jobname, current_version, _mtime(current_jdl))
        os.rename(current_jdl, f"{jdl.jdl_path}/saved/{saved}{jdl.extension}")
        if os.path.isfile(current_script):
            os.rename(current_script, f"{jdl.scripts_path}/saved/{saved}.sh")
    shutil.copyfile(jdl_file, current_jdl)
    if os.path.isfile(script_file):
        shutil.copyfile(script_file, current_script)
    else:
        logger.warning(f"No script found for the saved version {vid} of {jobname}")
    return version, saved


# ----------
# Diff


def _definition_lines(content):
    return json.dumps(content, indent=2, default=str).splitlines()


def _unified(old_lines, new_lines, old_label, new_label):
    """Unified diff as text (the lines of a script may not end with a newline)"""
    return "\n".join(difflib.unified_diff(old_lines, new_lines, old_label, new_label, lineterm=""))


def diff(jobname, from_vid, to_vid):
    """Unified diffs between two versions: {"definition": str, "script": str} (empty if identical)"""
    check_jobname(jobname)
    old_content, old_script = _read(jobname, from_vid)
    new_content, new_script = _read(jobname, to_vid)
    return {
        "definition": _unified(_definition_lines(old_content), _definition_lines(new_content), from_vid, to_vid),
        "script": _unified(old_script.splitlines(), new_script.splitlines(), f"{from_vid} script", f"{to_vid} script"),
    }
