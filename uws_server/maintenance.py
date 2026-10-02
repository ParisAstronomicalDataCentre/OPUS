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
- archived jobs that still have result files (e.g. archived by a previous version, which kept the files): files
  removed if applied, as when a job is archived

Without apply, nothing is changed (dry run): the job manager is only asked for the phase of the jobs.

The changes applied can be selected (select: categories among to_archive, to_delete, phase and archived_files, all
by default), and
the jobs to archive can be deleted instead (archive_action="delete").
"""

import datetime as dt

from . import storage
from .settings import DT_FMT, TERMINAL_PHASES, logger, settings
from .uws_classes import Job, JobList, User

# Categories of the jobs in the report
OK = "ok"
ARCHIVED = "archived"  # already archived
ARCHIVED_FILES = "archived_files"  # already archived, with result files still to remove
TO_ARCHIVE = "to_archive"  # after its destruction time
TO_DELETE = "to_delete"  # after its destruction time, cannot be archived (other phase, or no ARCHIVED phase)
PHASE = "phase"  # phase to update from the job manager
DATES = "dates"  # inconsistent dates
ERROR = "error"  # error while checking or applying

# Categories with a change to apply, and actions for the jobs to archive
APPLICABLE = [TO_ARCHIVE, TO_DELETE, PHASE, ARCHIVED_FILES]
ARCHIVE_ACTIONS = ["archive", "delete"]


def _date(value):
    return dt.datetime.strptime(value, DT_FMT) if value else None


def jobnames_in_db():
    """Job names of all the jobs in the database (also of deleted job definitions)"""
    job_storage = getattr(storage, settings.STORAGE + "JobStorage")()
    with job_storage.get_session() as session:
        return sorted(r[0] for r in session.query(job_storage.Job.jobname).distinct() if r[0])


def check_job(job, now, apply=False, select=None, archive_action="archive"):
    """Checks (and changes if apply) for a job, return a record for the report

    select: categories of the changes to apply (see APPLICABLE, all if None), the other changes are only reported
    archive_action: "archive", or "delete" to delete the jobs to archive
    """
    select = APPLICABLE if select is None else select
    apply_phase = apply and PHASE in select
    apply_archive = apply and TO_ARCHIVE in select
    apply_delete = apply and TO_DELETE in select
    apply_files = apply and ARCHIVED_FILES in select
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
        if job.result_files_dirs():
            # archived, but its result files were kept (e.g. archived by a previous version)
            record["categories"].append(ARCHIVED_FILES)
            record["actions"].append(f"result files {'removed' if apply_files else 'to remove'} (already archived)")
            if apply_files:
                job.remove_result_files()
        else:
            record["categories"].append(ARCHIVED)
    # Phase from the job manager (jobs not in a terminal phase)
    if job.phase not in TERMINAL_PHASES and job.phase not in ["PENDING", "UNKNOWN"]:
        manager_phase = job.get_status() if apply_phase else job.manager.get_status(job)
        if manager_phase != record["phase"]:
            record["categories"].append(PHASE)
            verb = "updated" if apply_phase else "to update"
            record["actions"].append(f"phase {verb}: {record['phase']} -> {manager_phase} (from the job manager)")
            record["phase"] = manager_phase
    # Destruction time
    if destruction and destruction < now and job.phase != "ARCHIVED":
        phase = record["phase"]
        if settings.USE_ARCHIVED_PHASE and phase in ["COMPLETED", "ABORTED", "ERROR"]:
            record["categories"].append(TO_ARCHIVE)
            if archive_action == "delete":
                verb = "deleted" if apply_archive else "to delete"
                record["actions"].append(f"{verb} instead of archived (destruction time passed)")
                if apply_archive:
                    job.delete()
                    record["phase"] = "DELETED"
            else:
                record["actions"].append(f"{'archived' if apply_archive else 'to archive'} (destruction time passed)")
                if apply_archive:
                    job.archive()
                    record["phase"] = "ARCHIVED"
        else:
            record["categories"].append(TO_DELETE)
            verb = "deleted" if apply_delete else "to delete"
            record["actions"].append(f"{verb} (destruction time passed, phase {phase})")
            if apply_delete:
                job.delete()
                record["phase"] = "DELETED"
    if not record["categories"]:
        record["categories"].append(OK)
    return record


def run(jobnames=None, apply=False, select=None, archive_action="archive"):
    """Maintenance of the jobs (all the jobs if jobnames is None), returns the report:
    {"apply": bool, "applied": [categories], "archive_action": str, "date": str, "jobs": [records],
    "summary": {category: count}}

    select: categories of the changes to apply (see APPLICABLE, all if None)
    archive_action: "archive", or "delete" to delete the jobs to archive (see ARCHIVE_ACTIONS)
    """
    select = list(APPLICABLE) if select is None else list(select)
    unknown = [c for c in select if c not in APPLICABLE]
    if unknown:
        raise ValueError(f"Unknown changes to apply: {', '.join(unknown)} (available: {', '.join(APPLICABLE)})")
    if archive_action not in ARCHIVE_ACTIONS:
        raise ValueError(f"Unknown action for the jobs to archive: {archive_action} ({' or '.join(ARCHIVE_ACTIONS)})")
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
                records.append(check_job(job, now, apply=apply, select=select, archive_action=archive_action))
            except Exception as e:
                logger.exception(f"Maintenance of job {jobid}")
                records.append({"jobname": jobname, "jobid": jobid, "phase": job.phase, "categories": [ERROR],
                                "issues": [str(e)], "actions": []})
            finally:
                job.close()
    summary = dict.fromkeys([OK, ARCHIVED, ARCHIVED_FILES, TO_ARCHIVE, TO_DELETE, PHASE, DATES, ERROR], 0)
    for record in records:
        for category in record["categories"]:
            summary[category] += 1
    report = {
        "apply": apply,
        "applied": select if apply else [],
        "archive_action": archive_action,
        "date": now.strftime(DT_FMT),
        "jobs": records,
        "summary": summary,
    }
    applied = f"applied ({', '.join(select) or 'nothing'}, jobs to archive: {archive_action})"
    logger.info(f"Maintenance {applied if apply else 'checked (dry run)'}: {summary}")
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
