# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 15:14:24 2015

@author: mservillat
"""

import os
import shutil
import urllib
import datetime as dt
import xml.etree.ElementTree
import storage
import managers
from settings import *


# ----------
# Set logger


import logging
logging.basicConfig(
    filename=LOG_FILE,
    format='[%(asctime)s] %(levelname)s %(module)s.%(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ---------
# Job class


class Job(object):
    """Job with UWS attributes and methods to create, set and shows job information"""

    def __init__(self, jobname, jobid, user,
                 get_attributes=False, get_parameters=False, get_results=False,
                 from_post=None, from_jobid_cluster=False):
        """Initialize from storage or from POST

        from_post should contain the request object if not None
        """
        # Job description
        if from_jobid_cluster:
            self.jobname = jobname
            self.jobid = None
            self.jobid_cluster = jobid
        else:
            self.jobname = jobname
            self.jobid = jobid
            self.jobid_cluster = None
        self.user = user
        self.wadl = None
        # Link to the storage, e.g. SQLiteStorage, see settings.py
        self.storage = storage.__dict__[STORAGE]()
        # Link to the job manager, e.g. SLURMManager, see settings.py
        self.manager = managers.__dict__[MANAGER]()
        # Fill job attributes
        if get_attributes or get_parameters or get_results:
            # Get from storage
            self.storage.read(self,
                              get_attributes=get_attributes,
                              get_parameters=get_parameters,
                              get_results=get_results,
                              from_jobid_cluster=from_jobid_cluster)
            # TODO: Check status on cluster, and change if necessary?
            # self.get_status()
        elif from_post:
            # Create a new PENDING job and save to storage
            now = dt.datetime.now()
            destruction = dt.timedelta(DESTRUCTION_INTERVAL)  # default interval for UWS server
            duration = dt.timedelta(0, 60)  # default duration of 60s, from wadl ?
            self.phase = 'PENDING'
            self.quote = None
            self.execution_duration = duration.total_seconds()
            self.error = None
            self.creation_time = now.strftime(DT_FMT)
            self.start_time = now.strftime(DT_FMT)
            self.end_time = (now + duration).strftime(DT_FMT)
            self.destruction_time = (now + destruction).strftime(DT_FMT)
            self.owner = user
            self.run_id = None
            self.parameters = {}
            self.results = {}
            # Set parameters from POSTed info
            self.set_from_post(from_post.POST, from_post.files)
        else:
            # Create blank job with None values, do not save to storage
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
            self.parameters = {}
            self.results = {}

    # ----------
    # Methods to read job description from WADL file

    def read_wadl(self):
        """Read job description from WADL file"""
        filename = WADL_PATH + self.jobname + '.wadl'
        job_wadl = {}
        parameters = {}
        results = {}
        try:
            with open(filename, 'r') as f:
                wadl_string = f.read()
            wadl_tree = xml.etree.ElementTree.fromstring(wadl_string)
            # Read parameters description
            params_block = wadl_tree.find(".//{http://wadl.dev.java.net/2009/02}representation[@id='parameters']")
            for p in params_block.getchildren():
                parameters[p.get('name')] = {
                    'type': p.get('type'),
                    'required': p.get('required'),
                    'default': p.get('default'),
                    'doc': p.getchildren()[0].text,
                }
            results_block = wadl_tree.find(".//{http://wadl.dev.java.net/2009/02}param[@name='result-id']")
            for r in results_block.getchildren():
                results[r.get('value')] = {
                    'mediaType': r.get('mediaType'),
                    'default': r.get('default'),
                    'doc': r.getchildren()[0].text,
                }
            logger.info('WADL read!')
        except IOError:
            # if file does not exist, continue and return an empty dict
            return {}
        job_wadl['parameters'] = parameters
        # TODO: Read results description from WADL
        job_wadl['results'] = results
        # TODO: Read expected duration from WADL
        job_wadl['duration'] = 60
        # TODO: Read expected quote from WADL?
        return job_wadl

    # ----------
    # Methods to get job attributes from storage or POST

    def set_from_post(self, post, files):
        """Set attributes and parameters from POST"""
        # Read WADL
        if not self.wadl:
            self.wadl = self.read_wadl()
        # Pop attributes keywords from POST or WADL
        self.execution_duration = post.pop('EXECUTION_DURATION', self.wadl.get('duration', EXECUTION_DURATION_DEF))
        # Set parameters from POST
        for pname, value in post.iteritems():
            if pname not in ['PHASE']:
                # TODO: use WADL to check if value is valid
                if pname not in self.wadl['parameters']:
                    logger.warning('Parameter {} not found in WADL'.format(pname))
                self.parameters[pname] = {'value': value, 'byref': False}
        # Upload files for multipart/form-data
        for fname, f in files.iteritems():
            upload_dir = UPLOAD_PATH + self.jobid
            if not os.path.isdir(upload_dir):
                os.makedirs(upload_dir)
            f.save(upload_dir + '/' + f.filename)
            # Parameter value is set to the file name on server
            value = f.filename
            self.parameters[fname] = {'value': value, 'byref': True}
        # Save to storage
        self.storage.save(self, save_attributes=True, save_parameters=True)

    # ----------
    # Methods to set a job attribute or parameter

    def set_attribute(self, attr, value):
        """Set job attribute and save to storage"""
        if attr in self.__dict__:
            self.__dict__[attr] = value
            #self.save_description()
            self.storage.save(self)
        else:
            raise KeyError(attr)

    def set_parameter(self, pname, value):
        """Set job attribute and save to storage"""
        self.parameters[pname]['value'] = value
        #self.save_description()
        self.storage.save(self, save_attributes=False, save_parameters=pname)

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
            params.append('"{}": "{}"'.format(pname, pdict['value']))
        return '{' + ', '.join(params) + '}'

    def parameters_to_xml(self, add_xmlns=True):
        """Returns the XML representation of job parameters"""
        if add_xmlns:
            xml_out = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<uws:parameters ',
                'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
                'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd">',
            ]
        else:
            xml_out = ['<uws:parameters>']
        # Add each parameter that has a value
        for pname, p in self.parameters.iteritems():
            if p['value']:
                name = pname
                value = urllib.quote_plus(p['value'])
                by_ref = str(p['byref']).lower()
                xml_out.append('<uws:parameter id="{}" byReference="{}">'.format(name, by_ref))
                xml_out.append(value)
                xml_out.append('</uws:parameter>')
        xml_out.append('</uws:parameters>')
        return ''.join(xml_out)

    def results_to_xml(self, add_xmlns=True):
        """Returns the XML representation of job results"""
        if add_xmlns:
            xml_out = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<uws:results ',
                'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
                'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
                'xmlns:xlink="http://www.w3.org/1999/xlink">',
            ]
        else:
            xml_out = ['<uws:results>']
        # Add each parameter that has a value
        for rname, r in self.results.iteritems():
            if r['url']:
                xml_out.append('<uws:result id="{}" xlink:href="{}"/>'.format(rname, r['url']))
        xml_out.append('</uws:results>')
        return ''.join(xml_out)

    def to_xml(self):
        """Returns the XML representation of a job (uws:job)"""

        def add_xml_node(name, value):
            """Add XML node"""
            if value:
                xml_node = '<uws:{}>{}</uws:{}>'.format(name, value, name)
            else:
                xml_node = '<uws:{} xsi:nil=\"true\"/>'.format(name)
            return xml_node

        xml_out = list([
            '<uws:job ',
            'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
            'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
            'xmlns:xlink="http://www.w3.org/1999/xlink">',
        ])
        xml_out.append(add_xml_node('jobId', self.jobid))
        xml_out.append(add_xml_node('phase', self.phase))
        xml_out.append(add_xml_node('executionduration', self.execution_duration))
        xml_out.append(add_xml_node('quote', self.quote))
        xml_out.append(add_xml_node('error', self.error))
        xml_out.append(add_xml_node('startTime', self.start_time))
        xml_out.append(add_xml_node('endTime', self.end_time))
        xml_out.append(add_xml_node('destruction', self.destruction_time))
        xml_out.append(add_xml_node('ownerId', self.owner))
        xml_out.append(self.parameters_to_xml(add_xmlns=False))
        xml_out.append(self.results_to_xml(add_xmlns=False))
        xml_out.append('</uws:job>')
        return ''.join(xml_out)

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
            raise UserWarning('Job {} is not in the PENDING state'.format(self.jobid))
        try:
            # Test if jobid_cluster is an integer
            jobid_cluster = int(jobid_cluster)
        except ValueError:
            raise RuntimeError('Bad jobid_cluster returned for job {}:\njobid_cluster:\n{}'
                               ''.format(self.jobid, jobid_cluster))
        # Change phase to QUEUED
        now = dt.datetime.now()
        duration = dt.timedelta(0, self.execution_duration)
        destruction = dt.timedelta(DESTRUCTION_INTERVAL)
        self.phase = 'QUEUED'
        self.start_time = now.strftime(DT_FMT)
        self.end_time = (now + duration).strftime(DT_FMT)
        self.destruction_time = (now + destruction).strftime(DT_FMT)
        self.jobid_cluster = jobid_cluster
        # Save changes to storage
        #self.save_description()
        self.storage.save(self)

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
            raise UserWarning('Job {} cannot be aborted while in phase {}'.format(self.jobid, self.phase))
        # Change phase to ABORTED
        now = dt.datetime.now()
        self.phase = 'ABORTED'
        self.end_time = now.strftime(DT_FMT)
        self.error = 'Job aborted by user ' + self.user
        # Save job description
        #self.save_description()
        self.storage.save(self)

    def delete(self):
        """Delete job

        Job can be deleted at any time.
        """
        if self.phase not in ['PENDING', 'COMPLETED']:
            # Send command to manager
            self.manager.delete(self)
        # Remove job from storage
        self.storage.delete(self)
        # Remove uploaded files corresponding to jobid if needed
        upload_dir = UPLOAD_PATH + self.jobid
        if os.path.isdir(upload_dir):
            shutil.rmtree(upload_dir)

    def get_status(self):
        """Get job status

        Job can get its status from the manager if it has been started and it is not in a final phase:
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        if self.phase not in ['PENDING', 'COMPLETED', 'ERROR', 'ABORTED', 'UNKNOWN']:
            # Send command to manager
            new_phase = self.manager.get_status(self)
            if new_phase != self.phase:
                # Change phase
                self.change_status(new_phase)
                # self.phase = new_phase
                # if new_phase == 'COMPLETED':
                #     # Get end_time
                #     self.end_time = self.manager.get_end_time(self)
                # self.save_description()
        return self.phase

    def change_status(self, new_phase, error=''):
        """Update job object, e.g. from a job_event or from get_status if phase has changed

        Job can be updated if it has been started and it is not in a final phase:
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        # TODO: DEBUG: PENDING and COMPLETED to be removed
        if self.phase in ['PENDING', 'QUEUED', 'EXECUTING', 'HELD', 'SUSPENDED', 'COMPLETED', 'ERROR']:
            # Change phase
            now = dt.datetime.now()
            # destruction = dt.timedelta(DESTRUCTION_INTERVAL)

            def nul(*args):
                """Simply change phase"""
                pass

            def phase_executing(job, error_msg):
                # Set job.start_time
                try:
                    job.start_time = job.manager.get_start_time(job)
                except:
                    logger.warning('job.manager.get_start_time(job) not responding, set start_time=now')
                    job.start_time = now.strftime(DT_FMT)
                # Estimates job.end_time from job.start_time + duration
                duration = dt.timedelta(0, self.execution_duration)
                end_time = dt.datetime.strptime(job.start_time, DT_FMT) + duration
                job.end_time = end_time.strftime(DT_FMT)

            def phase_completed(job, error_msg):
                # Set job.end_time
                try:
                    job.end_time = job.manager.get_end_time(job)
                except:
                    logger.warning('job.manager.get_end_time(job) not responding, set end_time=now')
                    job.end_time = now.strftime(DT_FMT)
                # TODO: Copy results to the UWS server if job is COMPLETED (done by cluster for now)

            def phase_error(job, error_msg):
                # Set job.end_time if not already in ERROR phase
                if job.phase != 'ERROR':
                    try:
                        job.end_time = job.manager.get_end_time(job)
                    except:
                        logger.warning('job.manager.get_end_time(job) not responding, set end_time=now')
                        job.end_time = now.strftime(DT_FMT)
                # Set job.error or add
                if job.error:
                    job.error += '. \n' + error_msg
                else:
                    job.error = error_msg

            # Switch
            cases = {'HELD': nul,
                     'SUSPENDED': nul,
                     'EXECUTING': phase_executing,
                     'COMPLETED': phase_completed,
                     'ERROR': phase_error}
            if new_phase not in cases:
                raise UserWarning('Phase change not allowed: {} --> {}'.format(self.phase, new_phase))
            # Run case
            cases[new_phase](self, error)
            # Update phase
            self.phase = new_phase
            # Save job description
            #self.save_description()
            self.storage.save(self)
        else:
            raise UserWarning('Job {} cannot be updated to {} while in phase {}'
                              ''.format(self.jobid, new_phase, self.phase))


# -------------
# JobList class


class JobList(object):
    """JobList with attributes and function to fetch from storage and return as XML"""

    def __init__(self, jobname, user, url):
        self.jobname = jobname
        self.user = user
        # The URL is required to include a link for each job in the XML representation
        self.url = url
        # Link to the storage, e.g. SQLiteStorage, see settings.py
        self.storage = storage.__dict__[STORAGE]()
        self.jobs = self.storage.get_list(self)

    def to_xml(self):
        """Returns the XML representation of jobs (uws:jobs)"""
        xml_out = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<uws:jobs ',
            'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
            'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
            'xmlns:xlink="http://www.w3.org/1999/xlink">',
        ]
        for job in self.jobs:
            href = self.url + '/' + job['jobid']
            xml_out.append('<uws:jobref id="{}" xlink:href="{}">'.format(job['jobid'], href))
            xml_out.append('<uws:phase>{}</uws:phase>'.format(job['phase']))
            xml_out.append('</uws:jobref>')
        xml_out.append('</uws:jobs>')
        return ''.join(xml_out)

    def to_html(self):
        """Returns the HTML representation of jobs"""
        html = ''
        for row in self.jobs:
            # Job ID
            jobid = row['jobid']
            job = Job(self.jobname, jobid, self.user, get_attributes=True, get_parameters=True, get_results=True)
            html += '<h3>Job ' + jobid + '</h3>'
            for k in JOB_ATTRIBUTES:
                html += k + ' = ' + str(job.__dict__[k]) + '<br>'
            # Parameters
            html += '<strong>Parameters:</strong><br>'
            for pname, p in job.parameters.iteritems():
                html += pname + ' = ' + p['value'] + '<br>'
            # Results
            html += '<strong>Results</strong><br>'
            for rname, r in job.results.iteritems():
                html += str(rname) + ': ' + r['url'] + '<br>'
        return html
