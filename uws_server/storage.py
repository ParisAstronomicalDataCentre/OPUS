#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Those classes handle the storage of the job information on the server
(e.g. files, relational database, ...)

Specific functions are expected for a storage class to save and read job information:
* save
* read
* delete
* get_job_list

Rq: sometimes we need access to the job attributes only, not the parameters or results,
therefore it is possible to retrieve only attributes, parameters or results so as to limit
the number of database access (in the case of a relational database)
"""

import datetime as dt
from settings import *


# ---------
# Exceptions/Warnings


class NotFoundWarning(Warning):
    """Warning used if Storage does not contain the information"""
    pass


# ---------
# Storage classes


class Storage(object):
    """
    Manage job information storage. This class defines required functions executed
    by the UWS server save(), read(), delete()
    """

    def save(self, job, save_attributes=True, save_parameters=True, save_results=True):
        """Save job information to storage (attributes, parameters and results)"""
        pass

    def read(self, job, get_attributes=True, get_parameters=True, get_results=True,
             from_jobid_cluster=False):
        """Read job information from storage"""
        pass

    def delete(self, job):
        """Delete job information from storage"""
        pass

    def get_list(self, joblist, phase=None):
        """Delete job information from storage"""
        pass


class SQLStorage(Storage):
    """Manage job information storage using SQL database

    This class defines required functions executed by the UWS server:
    save(), read(), delete()
    """

    # connector and cursor to be initialized by subclass
    conn = None
    cursor = None

    def _save_query(self, table_name, d):
        query = "INSERT OR REPLACE INTO {} ({}) VALUES ('{}')" \
                "".format(table_name, ", ".join(d.keys()), "', '".join(map(str, d.values())))
        query = query.replace("'None'", "NULL")
        self.cursor.execute(query)
        self.conn.commit()

    def _save_parameter(self, job, pname):
        # Save job parameter to db
        d = {
            'jobid': job.jobid,
            'name': pname,
            'value': job.parameters[pname]['value'],
            'byref': job.parameters[pname]['byref']
        }
        self._save_query('job_parameters', d)

    def _save_result(self, job, rname):
        # Save job parameter to db
        d = {
            'jobid': job.jobid,
            'name': rname,
            'url': job.results[rname]['url'],
            'mediaType': job.results[rname]['mediaType']
        }
        self._save_query('job_results', d)

    def save(self, job, save_attributes=True, save_parameters=False, save_results=False):
        """Save job information to storage (attributes, parameters and results)"""

        if save_attributes:
            # Save job description to db
            d = {col: str(job.__dict__[col]) for col in JOB_ATTRIBUTES}
            self._save_query('jobs', d)
        if save_parameters:
            if isinstance(save_parameters, str):
                # Save the given job parameter to db
                pname = save_parameters
                self._save_parameter(job, pname)
            else:
                # Save all job parameters to db
                for pname in job.parameters.keys():
                    self._save_parameter(job, pname)
        if save_results:
            # Save job results to db
            for rname in job.results.keys():
                self._save_result(job, rname)

    # noinspection PyTypeChecker
    def read(self, job, get_attributes=True, get_parameters=False, get_results=False, from_jobid_cluster=False):
        """Read job from storage"""
        # TODO: add owner and owner_pid to all SELECT (except if... admin?)
        if from_jobid_cluster:
            # Query db for jobname and jobid using jobid_cluster
            query = "SELECT jobname, jobid FROM jobs WHERE jobid_cluster='{}';".format(job.jobid_cluster)
            row = self.cursor.execute(query).fetchone()
            if not row:
                raise NotFoundWarning('Job with jobid_cluster={} NOT FOUND'.format(job.jobid_cluster))
            job.jobname = row['jobname']
            job.jobid = row['jobid']
        if get_attributes:
            # Query db for job description
            query = "SELECT * FROM jobs WHERE jobid='{}';".format(job.jobid)
            row = self.cursor.execute(query).fetchone()
            if not row:
                raise NotFoundWarning('Job "{}" NOT FOUND'.format(job.jobid))
            # creation_time = dt.datetime.strptime(job['creation_time'], DT_FMT)
            # start_time = dt.datetime.strptime(row['start_time'], DT_FMT)
            # end_time = dt.datetime.strptime(row['end_time'], DT_FMT)
            # destruction_time = dt.datetime.strptime(row['destruction_time'], DT_FMT)
            job.jobname = row['jobname']
            job.phase = row['phase']
            job.quote = row['quote']
            job.execution_duration = row['execution_duration']
            job.error = row['error']
            # self.creation_time = creation_time.strftime(DT_FMT)
            job.start_time = row['start_time']  # start_time.strftime(DT_FMT)
            job.end_time = row['end_time']  # end_time.strftime(DT_FMT)
            job.destruction_time = row['destruction_time']  # destruction_time.strftime(DT_FMT)
            job.owner = row['owner']
            job.owner_pid = row['owner_pid']
            job.run_id = row['run_id']
            job.jobid_cluster = row['jobid_cluster']
        if get_parameters:
            # Query db for job parameters
            query = "SELECT * FROM job_parameters WHERE jobid='{}';".format(job.jobid)
            params = self.cursor.execute(query).fetchall()
            # Format results to a parameter dict
            params_dict = {
                row['name']: {
                    'value': row['value'],
                    'byref': row['byref']
                }
                for row in params
            }
            job.parameters = params_dict
        else:
            job.parameters = {}
        if get_results:
            # Query db for job results
            query = "SELECT * FROM job_results WHERE jobid='{}';".format(job.jobid)
            results = self.cursor.execute(query).fetchall()
            results_dict = {
                row['name']: {
                    'url': row['url'],
                    'mediaType': row['mediaType']
                }
                for row in results
            }
            job.results = results_dict
        else:
            job.results = {}

    def delete(self, job):
        """Delete job from storage"""
        query1 = "DELETE FROM job_results WHERE jobid='{}';".format(job.jobid)
        self.cursor.execute(query1)
        query2 = "DELETE FROM job_parameters WHERE jobid='{}';".format(job.jobid)
        self.cursor.execute(query2)
        query3 = "DELETE FROM jobs WHERE jobid='{}';".format(job.jobid)
        self.cursor.execute(query3)
        self.conn.commit()

    def get_list(self, joblist, phase=None, check_user=True):
        """Query storage for job list"""
        query = "SELECT jobid, phase FROM jobs"
        where = ["jobname='{}'".format(joblist.jobname)]
        if phase:
            where_phase = []
            for p in phase:
                where_phase.append("phase='{}'".format(p))
            where.append('({})'.format(" OR ".join(where_phase)))
        if check_user:
            if joblist.user.name not in ['admin']:
                where.append("owner='{}'".format(joblist.user.name))
                where.append("owner_pid='{}'".format(joblist.user.pid))
        query += " WHERE " + " AND ".join(where)
        query += " ORDER BY start_time DESC;"
        logger.debug('query = {}'.format(query))
        jobs = self.cursor.execute(query).fetchall()
        return jobs


class SQLiteStorage(SQLStorage):
    """Manage job information storage using SQLite"""

    def __init__(self, db_file=SQLITE_FILE):
        # Get connector to db_file

        import sqlite3

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = dict_factory  # sqlite3.Row  #
        self.cursor = self.conn.cursor()

    def __del__(self):
        self.cursor.close()
        self.conn.close()


class PostgreSQLStorage(SQLStorage):
    """Manage job information storage using PostgreSQL"""

    def __init__(self, host=PGSQL_HOST, port=PGSQL_PORT, database=PGSQL_DATABASE,
                 user=PGSQL_USER, password=PGSQL_PASSWORD):
        # Get connector to db_file
        import psycopg2
        import psycopg2.extras
        self.conn = psycopg2.connect(host=host, port=port, database=database,
                                     user=user, password=password)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def __del__(self):
        self.cursor.close()
        self.conn.close()
