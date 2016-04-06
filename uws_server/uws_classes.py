#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Defines classes for UWS objects job and job_list
"""

import shutil
import urllib
import datetime as dt
import xml.etree.ElementTree as ETree

import uws_jdl
import storage
import managers
import voprov
from settings import *


# ---------
# User class


class User(object):
    """A user is defined by a name and a persistent ID (PID) or token
    The PID remains constant for a given user using a given client.
    Ideally it is a more general PID set during the authentication (e.g with eduGain/Shibboleth).
    The user name/pid can be sent via Basic access authentication
    """

    def __init__(self, name='anonymous', pid='anonymous'):
        self.name = name
        self.pid = pid


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
        # Prepare jdl attribute, e.g. WADL, see settings.py
        self.jdl = uws_jdl.__dict__[JDL]()
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
            duration = dt.timedelta(0, 60)  # default duration of 60s, from jdl ?
            self.phase = 'PENDING'
            self.quote = None
            self.execution_duration = duration.total_seconds()
            self.error = None
            self.creation_time = now.strftime(DT_FMT)
            self.start_time = now.strftime(DT_FMT)
            self.end_time = (now + duration).strftime(DT_FMT)
            self.destruction_time = (now + destruction).strftime(DT_FMT)
            self.owner = user.name
            self.owner_pid = user.pid
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
            self.owner_pid = None
            self.run_id = None
            self.parameters = {}
            self.results = {}

    # ----------
    # Methods to read job description from JDL file

    def get_result_filename(self, rname):
        """Get the filename corresponding to the result name"""
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        if not self.parameters:
            # need to read all parameters
            self.storage.read(self, get_attributes=False, get_parameters=True, get_results=False)
        if rname in self.parameters:
            # The result filename is a defined parameter of the job
            fname = self.parameters[rname]['value']
            fname = fname.split('file://')[-1]
        elif rname in self.jdl.content['parameters']:
            # The result filename is a parameter with a default value in the JDL
            fname = self.jdl.content['parameters'][rname]['default']
        else:
            # The result filename is the name given as default in the JDL
            fname = self.jdl.content['results'][rname]['default']
        logger.debug('Result filename for {} is {}'.format(rname, fname))
        return fname

    # ----------
    # Methods to get job attributes from storage or POST

    def set_from_post(self, post, files):
        """Set attributes and parameters from POST"""
        # Read JDL
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        # Pop attributes keywords from POST or JDL
        self.execution_duration = int(post.pop('EXECUTION_DURATION', self.jdl.content.get('executionduration', EXECUTION_DURATION_DEF)))
        self.quote = int(post.pop('QUOTE', self.jdl.content.get('quote', self.execution_duration)))
        # Set parameters from POST
        for pname, value in post.iteritems():
            if pname not in ['PHASE']:
                # TODO: use JDL to check if value is valid
                byref = False
                if pname not in self.jdl.content['parameters']:
                    logger.warning('Parameter {} not found in JDL'.format(pname))
                else:
                    ptype = self.jdl.content['parameters'][pname]['type']
                    if 'anyURI' in ptype:
                        byref = True
                self.parameters[pname] = {'value': value, 'byref': byref}
        # TODO: add default parameters values from JDL
        # Upload files for multipart/form-data
        for fname, f in files.iteritems():
            upload_dir = '{}/{}'.format(UPLOAD_PATH, self.jobid)
            if not os.path.isdir(upload_dir):
                os.makedirs(upload_dir)
            f.save(upload_dir + '/' + f.filename)
            logger.info('Parameter {} is a file and was downloaded ({})'.format(fname, f.filename))
            # Parameter value is set to the file name on server
            value = 'file://' + f.filename
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

    def parameters_to_bash(self, separator='\n', get_files=False):
        """Make parameter file content for given job

        Returns:
            All parameters as a list of bash variables
        """
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        params = ['# Required parameters']
        files = {'URI': [], 'form': []}
        # Required parameters
        for pname, pdict in self.parameters.iteritems():
            pvalue = pdict['value']
            if get_files:
                # Prepare file upload and convert param value for files
                # Test if file is given as a URI, prefixed by http*
                if any(s in pvalue for s in ['http://', 'https://']):
                    files['URI'].append(pvalue)
                    pvalue = pvalue.split('/')[-1]
                # Test if file was uploaded from the form, and given the "file://" prefix (see self.set_from_post())
                if 'file://' in pvalue:
                    pvalue = pvalue.split('/')[-1]
                    files['form'].append(pvalue)
            params.append(pname + '=\"' + pvalue + '\"')
        # Results
        params.append('# Results')
        for rname, rdict in self.jdl.content['results'].iteritems():
            if rname in self.parameters:
                rvalue = self.parameters[rname]['value']
                if 'file://' in rvalue:
                    if get_files:
                        rvalue = rvalue.split('/')[-1]
            else:
                rvalue = rdict['default']
                params.append(rname + '=\"' + rvalue + '\"')
        # Other parameters
        params.append('# Other parameters')
        for pname, pdict in self.jdl.content['parameters'].iteritems():
            if (pname not in self.parameters) and (pname not in self.results):
                params.append(pname + '=\"' + pdict['default'] + '\"')
        # Return list of bash variables
        if get_files:
            return separator.join(params), files
        else:
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

    def _parameters_to_xml_fill(self, xml_params):
        # Add each parameter that has a value
        for pname, p in self.parameters.iteritems():
            if p['value']:
                value = urllib.quote_plus(urllib.unquote_plus(p['value']))
                by_ref = str(p['byref']).lower()
                ETree.SubElement(xml_params, 'uws:parameter', attrib={'id': pname, 'byReference': by_ref}).text = value

    def parameters_to_xml(self):
        """Returns the XML representation of job parameters"""
        xmlns_uris = {'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
                      'xmlns:xlink': 'http://www.w3.org/1999/xlink',
                      'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                      'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'}
        xml_params = ETree.Element('uws:parameters', attrib=xmlns_uris)
        # Add each parameter that has a value
        self._parameters_to_xml_fill(xml_params)
        return ETree.tostring(xml_params)

    def _results_to_xml_fill(self, xml_results):
        for rname, r in self.results.iteritems():
            if r['url']:
                ETree.SubElement(xml_results, 'uws:result', attrib={'id': rname, 'xlink:href': r['url']})

    def results_to_xml(self):
        """Returns the XML representation of job results"""
        xmlns_uris = {'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
                      'xmlns:xlink': 'http://www.w3.org/1999/xlink',
                      'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                      'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'}
        xml_results = ETree.Element('uws:results', attrib=xmlns_uris)
        # Add each result that has a value
        self._results_to_xml_fill(xml_results)
        return ETree.tostring(xml_results)

    def to_xml(self):
        """Returns the XML representation of a job (uws:job)"""

        def add_sub_elt(root, tag, value, attrib=None):
            if value:
                if not attrib:
                    attrib = {}
                ETree.SubElement(root, tag, attrib=attrib).text = str(value)
            else:
                ETree.SubElement(root, tag, attrib={'xsi:nil': 'true'})

        xmlns_uris = {'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
                      'xmlns:xlink': 'http://www.w3.org/1999/xlink',
                      'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                      'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'}
        xml_job = ETree.Element('uws:job', attrib=xmlns_uris)
        add_sub_elt(xml_job, 'uws:jobId', self.jobid)
        add_sub_elt(xml_job, 'uws:phase', self.phase)
        add_sub_elt(xml_job, 'uws:executionduration', self.execution_duration)
        add_sub_elt(xml_job, 'uws:quote', self.quote)
        add_sub_elt(xml_job, 'uws:error', self.error)
        add_sub_elt(xml_job, 'uws:startTime', self.start_time)
        add_sub_elt(xml_job, 'uws:endTime', self.end_time)
        add_sub_elt(xml_job, 'uws:destruction', self.destruction_time)
        add_sub_elt(xml_job, 'uws:ownerId', self.owner)
        xml_params = ETree.SubElement(xml_job, 'uws:parameters')
        self._parameters_to_xml_fill(xml_params)
        xml_results = ETree.SubElement(xml_job, 'uws:results')
        self._results_to_xml_fill(xml_results)
        return ETree.tostring(xml_job)

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
        self.storage.save(self)

    def abort(self):
        """Abort job

        Job can be aborted if it is in one of the following states:
        - PENDING
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        # TODO: check if user has rights to abort job! (i.e. is owner or super_user)
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
        self.error = 'Job aborted by user ' + self.user.name
        # Save job description
        self.storage.save(self)

    def delete(self):
        """Delete job

        Job can be deleted at any time.
        """
        # TODO: check if user has rights to delete job! (i.e. is owner or super_user)
        if self.phase not in ['PENDING']:
            # Send command to manager
            self.manager.delete(self)
        # Remove uploaded files corresponding to jobid if needed
        upload_dir = '{}/{}'.format(UPLOAD_PATH, self.jobid)
        if os.path.isdir(upload_dir):
            shutil.rmtree(upload_dir)
        # Remove jobdata files corresponding to jobid if needed
        jobdata_dir = '{}/{}'.format(JOBDATA_PATH, self.jobid)
        if os.path.isdir(jobdata_dir):
            shutil.rmtree(jobdata_dir)
        # Remove job from storage
        self.storage.delete(self)

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
        return self.phase

    def change_status(self, new_phase, error=''):
        """Update job object, e.g. from a job_event or from get_status if phase has changed

        Job can be updated if it has been started and it is not in a final phase:
        - QUEUED / HELD / SUSPENDED
        - EXECUTING
        """
        # TODO: DEBUG: PENDING and COMPLETED to be removed, as no signals are expected for those phases
        if self.phase in ['PENDING', 'QUEUED', 'EXECUTING', 'HELD', 'SUSPENDED', 'COMPLETED', 'ERROR']:
            # Change phase
            now = dt.datetime.now()
            # destruction = dt.timedelta(DESTRUCTION_INTERVAL)

            def nul(*args):
                # Simply change phase
                pass

            def phase_executing(job, error_msg):
                # Set job.start_time
                job.start_time = now.strftime(DT_FMT)
                # Estimates job.end_time from job.start_time + duration
                duration = dt.timedelta(0, self.execution_duration)
                end_time = dt.datetime.strptime(job.start_time, DT_FMT) + duration
                job.end_time = end_time.strftime(DT_FMT)

            def phase_completed(job, error_msg):
                if not job.jdl.content:
                    job.jdl.read(job.jobname)
                # Copy back results from cluster
                job.manager.get_results(job)
                # Check results and all links to db (maybe not all results listed in JDL have been created)
                for rname, r in job.jdl.content['results'].iteritems():
                    rfname = job.get_result_filename(rname)
                    rfpath = '{}/{}/results/{}'.format(JOBDATA_PATH, job.jobid, rfname)
                    if os.path.isfile(rfpath):
                        # /get_result_file/<jobname>/<jobid>/<rname>/<fname>
                        url = '{}/get_result_file/{}/{}/{}'.format(BASE_URL, job.jobid, rname, rfname)
                        job.results[rname] = {'url': url, 'mediaType': r['mediaType']}
                        logger.info('add result ' + rname + ' ' + str(r))
                # Set job.end_time
                job.end_time = now.strftime(DT_FMT)
                # Link job logs stdout and stderr (added as a result)
                rfdir = '{}/{}/results/'.format(JOBDATA_PATH, job.jobid)
                if os.path.isdir(rfdir):
                    rname = 'stdout'
                    rfname = 'stdout'

                    url = '{}/get_result_file/{}/{}/{}'.format(BASE_URL, job.jobid, rname, rfname)
                    job.results[rname] = {'url': url, 'mediaType': 'text/plain'}
                    logger.info('add stdout.log file to results')
                else:
                    logger.warning('CANNOT add logs to results')
                # Create Provenance XML file (added as a result)
                pdoc = voprov.job2prov(job)
                if os.path.isdir(rfdir):
                    # PROV XML
                    rname = 'provxml'
                    rfname = 'provenance.xml'
                    voprov.prov2xml(pdoc, rfdir + rfname)
                    #pdoc.serialize(rfdir + rfname, format='xml')
                    url = '{}/get_result_file/{}/{}/{}'.format(BASE_URL, job.jobid, rname, rfname)
                    job.results[rname] = {'url': url, 'mediaType': 'text/xml'}
                    logger.info('add provenance.xml file to results')
                    # PROV SVG
                    rname = 'provsvg'
                    rfname = 'provenance.svg'
                    voprov.prov2svg(pdoc, rfdir + rfname)
                    #pdoc.serialize(rfdir + rfname, format='xml')
                    url = '{}/get_result_file/{}/{}/{}'.format(BASE_URL, job.jobid, rname, rfname)
                    job.results[rname] = {'url': url, 'mediaType': 'image/svg+xml'}
                    logger.info('add provenance.svg file to results')
                else:
                    logger.warning('CANNOT add provenance file to results')


            def phase_error(job, error_msg):
                # Set job.end_time if not already in ERROR phase
                if job.phase != 'ERROR':
                    job.end_time = now.strftime(DT_FMT)
                # Set job.error or add
                if job.error:
                    job.error += '. ' + error_msg
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
            self.storage.save(self, save_results=True)
        else:
            raise UserWarning('Job {} cannot be updated to {} while in phase {}'
                              ''.format(self.jobid, new_phase, self.phase))


# -------------
# JobList class


class JobList(object):
    """JobList with attributes and function to fetch from storage and return as XML"""

    def __init__(self, jobname, user):
        self.jobname = jobname
        self.user = user
        # The URL is required to include a link for each job in the XML representation
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
            href = '{}/{}/{}'.format(BASE_URL, self.jobname, job['jobid'])
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
                html += '{} ({}): {} <br>'.format(str(rname), r['mediaType'], r['url'])
        return html
