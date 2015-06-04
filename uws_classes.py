# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 15:14:24 2015

@author: mservillat
"""

import os
import urllib
import datetime
import xml.etree.ElementTree
import managers
from settings import *


# ----------
# Utility variables


job_cols = ['jobid', 'jobname', 'phase', 'quote', 'execution_duration', 'error',
            'start_time', 'end_time', 'destruction_time', 'owner', 'run_id', 'jobid_cluster']
job_params_cols = ['jobid', 'name', 'value', 'byref']
job_results_cols = ['jobid', 'name', 'url']

dt_fmt = '%Y-%m-%dT%H:%M:%S'

phases = [
    'PENDING',
    'QUEUED',
    'EXECUTING',
    'COMPLETED',
    'ERROR',
    'ABORTED',
    'UNKNOWN',
    'HELD',
    'SUSPENDED'
]


# ---------
# Job class


class Job(object):
    """Job with attributes and function to fetch from db and return as XML"""

    def __init__(self, jobname, jobid, user, db, manager=MANAGER,
                 get_description=False, get_params=False, get_results=False,
                 from_post=None):
        """Initialize from db or from POST

        from_post should contain the request object if not None
        """
        # Job description
        self.jobname = jobname
        self.jobid = jobid
        self.user = user
        # Internal information:
        # Connector to UWS database
        self.db = db
        # Link to the job manager, e.g. SLURMManager, see settings.py
        self.manager = managers.__dict__[manager]()
        # Fill job attributes
        if get_description:
            # Get from db
            self.get_from_db()
            # Check status on cluster, and change if ncessary
            self.get_status()
        elif from_post:
            now = datetime.datetime.now()
            destruction = datetime.timedelta(DESTRUCTION_INTERVAL)  # default interval for UWS server
            duration = datetime.timedelta(0, 60)  # default duration of 60s, from wadl ?
            # Create a new PENDING job and save to db
            self.phase = 'PENDING'
            self.quote = None
            self.execution_duration = duration.total_seconds()
            self.error = None
            self.creation_time = now.strftime(dt_fmt)
            self.start_time = now.strftime(dt_fmt)
            self.end_time = (now + duration).strftime(dt_fmt)
            self.destruction_time = (now + destruction).strftime(dt_fmt)
            self.owner = user
            self.run_id = None
            self.jobid_cluster = None
            self.parameters = {}
            self.results = {}
            # Set parameters from POSTed info
            self.set_from_post(from_post.POST, from_post.files)
            # Save to db
            self.save()
        else:
            # Create blank job with None values, do not save to db
            self.phase = 'UNKONWN'
            self.quote = None
            self.execution_duration = None
            self.error = None
            self.creation_time = None
            self.start_time = None
            self.end_time = None
            self.destruction_time = None
            self.owner = None
            self.run_id = None
            self.jobid_cluster = None
            self.parameters = {}
            self.results = {}
        if get_params:
            self.get_parameters()
        if get_results:
            self.get_results()

    # ----------
    # Methods to read job description from WADL file

    def read_wadl(self):
        """Read job description from WADL file"""
        filename = WADL_PATH + self.jobname + '.wadl'
        job_wadl = {}
        params = {}
        results = {}
        try:
            with open(filename,'r') as f:
                wadl_string = f.read()
            wadl_tree = xml.etree.ElementTree.fromstring(wadl_string)
            # Read parameters description
            params_block = wadl_tree.find(".//{http://wadl.dev.java.net/2009/02}representation[@id='parameters']")
            for p in params_block.getchildren():
                params[p.get('name')] = {
                    'type': p.get('type'),
                    'required': p.get('required'),
                    'default': p.get('default'),
                    'prompt': p.getchildren()[0].text
                }
        except IOError:
            # if file does not exist, continue and return an empty dict
            return {}
        job_wadl['parameters'] = params
        # TODO: Read results description from WADL
        job_wadl['results'] = results
        # TODO: Read expected duration from WADL
        job_wadl['duration'] = 60
        # TODO: Read expected quote from WADL?
        return job_wadl

    # ----------
    # Methods to get job attributes from db of POST

    def get_parameters(self):
        """Query db for job parameters"""
        query = "SELECT * FROM job_parameters WHERE jobid='" + self.jobid + "';"
        params = self.db.execute(query).fetchall()
        params_dict = {row['name']: {'value': row['value'], 'byref': row['byref']} for row in params}
        self.parameters = params_dict

    def get_results(self):
        """ Query db for job results"""
        query = "SELECT * FROM job_results WHERE jobid='" + self.jobid + "';"
        results = self.db.execute(query).fetchall()
        results_dict = {row['name']: {'url': row['url']} for row in results}
        self.results = results_dict

    def get_from_db(self):
        """Query db for job description"""
        query = "SELECT * FROM jobs WHERE jobid='" + self.jobid + "';"
        job = self.db.execute(query).fetchone()
        # creation_time = datetime.datetime.strptime(job['creation_time'], "%Y-%m-%dT%H:%M:%S")
        start_time = datetime.datetime.strptime(job['start_time'], dt_fmt)
        end_time = datetime.datetime.strptime(job['end_time'], dt_fmt)
        destruction_time = datetime.datetime.strptime(job['destruction_time'], dt_fmt)
        self.jobname = job['jobname']
        self.phase = job['phase']
        self.quote = job['quote']
        self.execution_duration = job['execution_duration']
        self.error = job['error']
        # self.creation_time = creation_time.strftime(dt_fmt)
        self.start_time = start_time.strftime(dt_fmt)
        self.end_time = end_time.strftime(dt_fmt)
        self.destruction_time = destruction_time.strftime(dt_fmt)
        self.owner = job['owner']
        self.run_id = job['run_id']
        self.jobid_cluster = job['jobid_cluster']
        self.parameters = {}
        self.results = {}

    def set_from_post(self, post, files):
        """Set attributes and parameters from POST"""
        # Read WADL
        wadl = self.read_wadl()
        print str(wadl)
        # Pop attributes keywords from POST or WADL
        self.execution_duration = post.pop('EXECUTION_DURATION', wadl.get('duration', None))
        # Set parameters from POST
        print str(post.__dict__)
        for pname, value in post.iteritems():
            if pname not in ['PHASE']:
                # TODO: use WADL to check if value is valid
                self.parameters[pname] = {'value': value, 'byref': False}
        # Upload files for multipart/form-data
        print str(files.__dict__)
        for fname, f in files.iteritems():
            upload_dir = 'uploads/' + self.jobid
            if not os.path.isdir(upload_dir):
                os.makedirs(upload_dir)
            f.save(upload_dir + '/' + f.filename)
            value = f.filename
            self.parameters[fname] = {'value': value, 'byref': True}


    # ----------
    # Methods to save job attributes to db

    def save_query(self, table_name, d):
        query = "INSERT OR REPLACE INTO " + table_name + " (" + ", ".join(d.keys()) + ") " \
                "VALUES ('" + "', '".join(map(str, d.values())) + "')"
        query = query.replace("'None'", "NULL")
        self.db.execute(query)

    def save_parameter(self, pname):
        """Save job parameters to db"""
        d = {'jobid': self.jobid,
             'name': pname,
             'value': self.parameters[pname]['value'],
             'byref': self.parameters[pname]['byref']}
        self.save_query('job_parameters', d)

    def save_parameters(self):
        """Save job parameters to db"""
        for pname in self.parameters.keys():
            self.save_parameter(pname)

    def save_results(self):
        """Save job results to db"""
        for rname, r in self.results.iteritems():
            d = {'jobid': self.jobid,
                 'name': rname,
                 'url': r['url']}
            self.save_query('job_results', d)

    def save_description(self):
        """Save job description to db"""
        d = {col: str(self.__dict__[col]) for col in job_cols}
        self.save_query('jobs', d)

    def save(self):
        """Save job to db"""
        self.save_description()
        self.save_parameters()
        self.save_results()

    # ----------
    # Methods to set a job attribute

    def set(self, attr, value):
        """Set job attribute and save to db"""
        if attr in self.__dict__:
            self.__dict__[attr] = value
            self.save_description()
        else:
            raise KeyError(attr)

    def set_destruction_time(self, destruction):
        self.destruction_time = datetime.datetime.strptime(destruction, dt_fmt)
        self.save_description()

    # ----------
    # Methods to export a job description

    def parameters_to_text(self, separator='\n'):
        """Make parameter file content for given job

        Returns:
            parameter list as a string
        """
        params = []
        for pname, pdict in self.parameters.iteritems():
            # TODO: save URI on UWS server if byref=True
            params.append(pname + '=' + pdict['value'])
        return separator.join(params)

    def parameters_to_json(self):
        """Make parameter file content for given job

        Returns:
            parameter list as a string
        """
        params = []
        for pname, pdict in self.parameters.iteritems():
            params.append('"' + pname + '": "' + pdict['value'] + '"')
        return '{' + ', '.join(params) + '}'

    def parameters_to_xml(self, add_xmlns=True):
        """Returns the XML representation of job parameters"""
        if add_xmlns:
            xml = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<uws:parameters ',
                'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
                'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd">',
            ]
        else:
            xml = ['<uws:parameters>']
        # Add each parameter that has a value
        for pname, p in self.parameters.iteritems():
            if p['value']:
                name = pname
                value = urllib.quote_plus(p['value'])
                by_ref = str(p['byref']).lower()
                xml.append('<uws:parameter id="' + name + '" byReference="' + by_ref + '">')
                xml.append(value)
                xml.append('</uws:parameter>')
        xml.append('</uws:parameters>')
        return ''.join(xml)

    def results_to_xml(self, add_xmlns=True):
        """Returns the XML representation of job results"""
        if add_xmlns:
            xml = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<uws:results ',
                'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
                'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
                'xmlns:xlink="http://www.w3.org/1999/xlink">',
            ]
        else:
            xml = ['<uws:results>']
        # Add each parameter that has a value
        for rname, r in self.results.iteritems():
            if r['url']:
                xml.append('<uws:result id="' + rname + '" xlink:href="' + r['url'] + '"/>')
        xml.append('</uws:results>')
        return ''.join(xml)

    def to_xml(self):
        """Returns the XML representation of a job (uws:job)"""

        def add_xml_node(name, value):
            """Add XML node"""
            if value:
                xml = '<uws:%s>%s</uws:%s>' % (name, value, name)
            else:
                xml = '<uws:%s xsi:nil=\"true\"/>' % name
            return xml

        xml = list([
            '<uws:job ',
            'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
            'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
            'xmlns:xlink="http://www.w3.org/1999/xlink">',
        ])
        xml.append(add_xml_node('jobId', self.jobid))
        xml.append(add_xml_node('phase', self.phase))
        xml.append(add_xml_node('executionduration', self.execution_duration))
        xml.append(add_xml_node('quote', self.quote))
        xml.append(add_xml_node('startTime', self.start_time))
        xml.append(add_xml_node('endTime', self.end_time))
        xml.append(add_xml_node('destruction', self.destruction_time))
        xml.append(add_xml_node('ownerId', self.owner))
        xml.append(self.parameters_to_xml(add_xmlns=False))
        xml.append(self.results_to_xml(add_xmlns=False))
        xml.append('</uws:job>')
        return ''.join(xml)

    # ----------
    # Actions on a job

    def start(self):
        """Start job

        Job can be started only if it is in PENDING state
        """
        # Test if status is PENDING as expected
        if self.phase == 'PENDING':
            jobid_cluster = self.manager.start(self)
        else:
            raise RuntimeWarning('Job {} is not in the PENDING state'.format(self.jobid))
        try:
            # Test if jobid_cluster is an integer
            jobid_cluster = int(jobid_cluster)
        except ValueError:
            raise RuntimeError('Bad jobid_cluster returned for job {}:\njobid_cluster:\n{}'
                               ''.format(self.jobid, jobid_cluster))
        # Change phase to QUEUED
        now = datetime.datetime.now()
        duration = datetime.timedelta(0, self.execution_duration)
        destruction = datetime.timedelta(DESTRUCTION_INTERVAL)
        self.phase = 'QUEUED'
        self.start_time = now.strftime(dt_fmt)
        self.end_time = (now + duration).strftime(dt_fmt)
        self.destruction_time = (now + destruction).strftime(dt_fmt)
        self.jobid_cluster = jobid_cluster
        # Save changes to db
        self.save_description()

    def abort(self):
        """Abort job

        Job can be aborted if it is in one of the following states:
        - PENDING
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        if self.phase in ['PENDING']:
            pass
        elif self.phase in ['QUEUED', 'HELD', 'SUSPENDED', 'EXECUTING']:
            # Send command to manager
            self.manager.abort(self)
        else:
            raise RuntimeWarning('Job {} cannot be aborted while in phase {}'.format(self.jobid, self.phase))
        # Change phase to ABORTED
        now = datetime.datetime.now()
        self.phase = 'ABORTED'
        self.end_time = now.strftime(dt_fmt)
        self.error = 'Job aborted by user ' + self.user
        # Save job description
        self.save_description()

    def delete(self):
        """Delete job

        Job can be deleted at any time.
        """
        # Send command to manager
        self.manager.delete(self)
        # Clean db
        query = "DELETE FROM job_results WHERE jobid='" + self.jobid + "';"
        self.db.execute(query)
        query = "DELETE FROM job_parameters WHERE jobid='" + self.jobid + "';"
        self.db.execute(query)
        query = "DELETE FROM jobs WHERE jobid='" + self.jobid + "';"
        self.db.execute(query)
        # TODO: Remove uploaded files corresponding to jobid if needed

    def get_status(self):
        """Get job status

        Job can get its status if it has been started and it is not in a final phase:
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        if self.phase not in ['PENDING', 'COMPLETED', 'ERROR', 'ABORTED', 'UNKNOWN']:
            # Send command to manager
            new_phase = self.manager.get_status(self)
            if new_phase != self.phase:
                # Change phase
                self.phase = new_phase
                if new_phase == 'COMPLETED':
                    # TODO: copy results to the UWS server if job is COMPLETED (done by cluster for now)
                    # Get end_time
                    self.end_time = self.manager.get_end_time(self)
                self.save_description()
        return self.phase

    def change_status(self, phase, error=''):
        """Update job object, e.g. from a job_event or from

        Job need to be updated if it has been started and it is not in a final phase:
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        # TODO: DEBUG: PENDING to be removed as a PENDING job can only change status through start()
        if self.phase in ['PENDING', 'QUEUED', 'EXECUTING', 'HELD', 'SUSPENDED', 'COMPLETED']:
            # Change phase
            now = datetime.datetime.now()
            # destruction = datetime.timedelta(DESTRUCTION_INTERVAL)
            self.phase = phase

            def nul(*args):
                pass

            def phase_executing(job, error):
                duration = datetime.timedelta(0, self.execution_duration)
                job.start_time = now.strftime(dt_fmt)
                # Estimates end_time from start_time + duration
                job.end_time = (now + duration).strftime(dt_fmt)

            def phase_completed(job, error):
                job.end_time = now.strftime(dt_fmt)
                # job.end_time = job.manager.get_end_time()
                # TODO: copy results to the UWS server if job is COMPLETED (done by cluster for now)

            def phase_error(job, error):
                if job.error:
                    job.error += '\n' + error
                else:
                    job.error = error

            # Switch
            cases = {'HELD': nul,
                     'SUSPENDED': nul,
                     'EXECUTING': phase_executing,
                     'COMPLETED': phase_completed,
                     'ERROR': phase_error}
            # Run case
            cases[phase](self, error)
            # Save job description
            self.save_description()
        else:
            raise RuntimeWarning('Job {} cannot be updated to {} while in phase {}'
                                 ''.format(self.jobid, phase, self.phase))


# -------------
# JobList class


class JobList(object):
    """JobList with attributes and function to fetch from db and return as XML"""

    def __init__(self, jobname, user, url, db):
        self.jobname = jobname
        self.user = user
        # The URL is required to include a link for each job in the XML representation
        self.url = url
        self.db = db
        self.jobs = {}
        self.get_from_db()

    def get_from_db(self):
        """Query db for job list"""
        query = "SELECT jobid, phase FROM jobs"
        where = ["jobname='" + self.jobname + "'",
                 "owner='" + self.user + "'"]
        query += " WHERE " + " AND ".join(where) + ";"
        jobs = self.db.execute(query).fetchall()
        self.jobs = jobs

    def to_xml(self):
        """Returns the XML representation of jobs (uws:jobs)"""
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<uws:jobs ',
            'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
            'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
            'xmlns:xlink="http://www.w3.org/1999/xlink">',
        ]
        for job in self.jobs:
            href = self.url + '/' + job['jobid']
            xml.append('<uws:jobref id="' + job['jobid'] + '" xlink:href="' + href + '">')
            xml.append('<uws:phase>' + job['phase'] + '</uws:phase>')
            xml.append('</uws:jobref>')
        xml.append('</uws:jobs>')
        return ''.join(xml)

    def to_html(self):
        """Returns the HTML representation of jobs"""
        html = ''
        for job in self.jobs:
            # Job ID
            jobid = job['jobid']
            html += '<h3>Job ' + jobid + '</h3>'
            for k, v in dict(job).iteritems():
                html += k + ' = ' + str(v) + '<br>'
            # Parameters
            query = "select * from job_parameters where jobid = '" + jobid + "';"
            params = self.db.execute(query).fetchall()
            html += '<h4>Parameters</h4>'
            for param in params:
                html += param['name'] + ' = ' + param['value'] + '<br>'
            # Results
            query = "select * from job_results where jobid = '" + jobid + "';"
            results = self.db.execute(query).fetchall()
            html += '<h4>Results</h4>'
            for result in results:
                html += str(result['name']) + ': ' + result['url'] + '<br>'
        return html
