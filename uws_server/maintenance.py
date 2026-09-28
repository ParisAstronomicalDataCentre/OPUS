#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Maintenance of the jobs: checks, and changes if applied (apply=True)

For each job (all the jobs of the database, including archived jobs):
- consistency of the dates (creation, start, end, destruction)
- phase of the jobs not in a terminal phase, from the job manager (updated if applied)
- jobs after their destruction time: archived if applied (USE_ARCHIVED_PHASE, phases COMPLETED, ABORTED and
  ERROR), else deleted if applied (job stopped by the job manager if needed, files and database entries removed)

Without apply, nothing is changed (dry run): the job manager is only asked for the phase of the jobs.
"""

import datetime as dt

from . import storage
from .settings import DT_FMT, TERMINAL_PHASES, logger, settings
from .uws_classes import Job, JobList, User

# Categories of the jobs in the report
OK = "ok"
ARCHIVED = "archived"  # already archived
TO_ARCHIVE = "to_archive"  # after its destruction time
TO_DELETE = "to_delete"  # after its destruction time, cannot be archived (other phase, or no ARCHIVED phase)
PHASE = "phase"  # phase to update from the job manager
DATES = "dates"  # inconsistent dates
ERROR = "error"  # error while checking or applying


def _date(value):
    return dt.datetime.strptime(value, DT_FMT) if value else None


def jobnames_in_db():
    """Job names of all the jobs in the database (also of deleted job definitions)"""
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    with job_storage.get_session() as session:
        return sorted(r[0] for r in session.query(job_storage.Job.jobname).distinct() if r[0])


def check_job(job, now, apply=False):
    """Checks (and changes if apply) for a job, return a record for the report"""
    record = {
        "jobname": job.jobname,
        "jobid": job.jobid,
        "owner": job.owner,
        "phase": job.phase,
        "creation_time": job.creation_time,
        "start_time": job.start_time,
        "end_time": job.end_time,
        "destruction_time": job.destruction_time,
        "categories": [],
        "issues": [],
        "actions": [],  # changes to apply (apply=False) or applied (apply=True)
    }
    creation, start, end = _date(job.creation_time), _date(job.start_time), _date(job.end_time)
    destruction = _date(job.destruction_time)
    # Dates
    issues = []
    if creation and start and creation > start:
        issues.append("creation_time > start_time")
    if start and end and start > end:
        issues.append("start_time > end_time")
    if end and destruction and end > destruction:
        issues.append("end_time > destruction_time")
    if not start and job.phase not in ["PENDING", "QUEUED", "ARCHIVED"]:
        issues.append("start_time not set")
    if not end and job.phase in TERMINAL_PHASES:
        issues.append("end_time not set")
    if issues:
        record["categories"].append(DATES)
        record["issues"].extend(issues)
    if job.phase == "ARCHIVED":
        record["categories"].append(ARCHIVED)
    # Phase from the job manager (jobs not in a terminal phase)
    if job.phase not in TERMINAL_PHASES and job.phase not in ["PENDING", "UNKNOWN"]:
        manager_phase = job.get_status() if apply else job.manager.get_status(job)
        if manager_phase != record["phase"]:
            record["categories"].append(PHASE)
            verb = "updated" if apply else "to update"
            record["actions"].append(f"phase {verb}: {record['phase']} -> {manager_phase} (from the job manager)")
            record["phase"] = manager_phase
    # Destruction time
    if destruction and destruction < now and job.phase != "ARCHIVED":
        phase = record["phase"]
        if settings.USE_ARCHIVED_PHASE and phase in ["COMPLETED", "ABORTED", "ERROR"]:
            record["categories"].append(TO_ARCHIVE)
            record["actions"].append(f"{'archived' if apply else 'to archive'} (destruction time passed)")
            if apply:
                job.archive()
                record["phase"] = "ARCHIVED"
        else:
            record["categories"].append(TO_DELETE)
            record["actions"].append(f"{'deleted' if apply else 'to delete'} (destruction time passed, phase {phase})")
            if apply:
                job.delete()
                record["phase"] = "DELETED"
    if not record["categories"]:
        record["categories"].append(OK)
    return record


def run(jobnames=None, apply=False):
    """Maintenance of the jobs (all the jobs if jobnames is None), returns the report:
    {"apply": bool, "date": str, "jobs": [records], "summary": {category: count}}"""
    user = User("maintenance", settings.MAINTENANCE_TOKEN.get_secret_value())
    now = dt.datetime.now()
    records = []
    for jobname in jobnames or jobnames_in_db():
        joblist = JobList(jobname, user, where_owner=False, include_archived=True)
        try:
            jobids = [j["jobid"] for j in joblist.jobs]
        finally:
            joblist.close()
        for jobid in jobids:
            try:
                job = Job(jobname, jobid, user, get_attributes=True, get_parameters=True, get_results=True)
            except Exception as e:
                records.append({"jobname": jobname, "jobid": jobid, "categories": [ERROR], "issues": [str(e)],
                                "actions": []})
                continue
            try:
                records.append(check_job(job, now, apply=apply))
            except Exception as e:
                logger.exception(f"Maintenance of job {jobid}")
                records.append({"jobname": jobname, "jobid": jobid, "phase": job.phase, "categories": [ERROR],
                                "issues": [str(e)], "actions": []})
            finally:
                job.close()
    summary = dict.fromkeys([OK, ARCHIVED, TO_ARCHIVE, TO_DELETE, PHASE, DATES, ERROR], 0)
    for record in records:
        for category in record["categories"]:
            summary[category] += 1
    report = {"apply": apply, "date": now.strftime(DT_FMT), "jobs": records, "summary": summary}
    logger.info(f"Maintenance {'applied' if apply else 'checked (dry run)'}: {summary}")
    return report


def to_text(report):
    """Report as text (maintenance route for cron / just maintenance)"""
    lines = []
    for r in report["jobs"]:
        if r["categories"] == [OK] or r["categories"] == [ARCHIVED]:
            continue
        lines.append(f"[{r['jobname']} {r['jobid']} {r.get('creation_time')} {r.get('phase')}]")
        lines += [f"  {line}" for line in r["issues"] + r["actions"]]
    counts = ", ".join(f"{k}: {v}" for k, v in report["summary"].items() if v)
    lines.append(f"{len(report['jobs'])} jobs checked ({counts})")
    return "\n".join(lines)
