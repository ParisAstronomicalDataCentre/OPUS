#!/usr/bin/env python2
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
from blinker import signal
import uws_jdl
import storage
import managers
import voprov
from settings import *


# ---------
# Exceptions/Warnings


class JobAccessDenied(Exception):
    """User has no right to access job"""
    pass


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

    def __str__(self):
        return self.name


# ---------
# Job class


class Job(object):
    """Job with UWS attributes and methods to create, set and show job information"""

    def __init__(self, jobname, jobid, user,
                 get_attributes=False, get_parameters=False, get_results=False,
                 from_post=None, from_pid=False,
                 check_user=True):
        """Initialize from storage or from POST

        from_post should contain the request object if not None
        """
        # Job description
        if from_pid:
            self.jobname = jobname
            self.jobid = None
            self.pid = jobid
        else:
            self.jobname = jobname
            self.jobid = jobid
            self.pid = None
        self.user = user
        # Prepare jdl attribute, e.g. WADL, see settings.py
        self.jdl = uws_jdl.__dict__[JDL]()
        # Link to the storage, e.g. SQLiteStorage, see settings.py
        self.storage = storage.__dict__[STORAGE + 'JobStorage']()
        # Link to the job manager, e.g. SLURMManager, see settings.py
        self.manager = managers.__dict__[MANAGER + 'Manager']()
        # Fill job attributes
        if get_attributes or get_parameters or get_results:
            # Get from storage
            self.storage.read(self,
                              get_attributes=get_attributes,
                              get_parameters=get_parameters,
                              get_results=get_results,
                              from_pid=from_pid)
            if check_user:
                # Check if user has rights to manipulate the job
                if user.name != 'admin':
                    if self.owner == user.name:
                        if self.owner_pid != user.pid:
                            raise JobAccessDenied('User {} is the owner of the job but has a wrong PID'.format(user.name))
                    else:
                        raise JobAccessDenied('User {} is not the owner of the job'.format(user.name))
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
            self.start_time = None  # now.strftime(DT_FMT)
            self.end_time = None  # (now + duration).strftime(DT_FMT)
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
            now = dt.datetime.now()
            self.phase = 'UNKONWN'
            self.quote = None
            self.execution_duration = None
            self.error = None
            self.creation_time = now.strftime(DT_FMT)
            self.start_time = None
            self.end_time = None
            self.destruction_time = None
            self.owner = None
            self.owner_pid = None
            self.run_id = None
            self.parameters = {}
            self.results = {}


    # ----------
    # Method to read job description from JDL file
    # ----------


    def get_result_filename(self, rname):
        """Get the filename corresponding to the result name"""
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        if not self.parameters:
            # need to read all parameters
            self.storage.read(self, get_attributes=True, get_parameters=True, get_results=True)
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
    # Method to get job attributes from storage or POST
    # ----------


    def set_from_post(self, post, files):
        """Set attributes and parameters from POST"""
        # Read JDL
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        # Pop attributes keywords from POST or JDL
        self.execution_duration = int(post.pop('EXECUTION_DURATION', self.jdl.content.get('executionduration', EXECUTION_DURATION_DEF)))
        self.quote = int(post.pop('QUOTE', self.jdl.content.get('quote', self.execution_duration)))
        # Search inputs in POST/files
        upload_dir = '{}/{}'.format(UPLOAD_PATH, self.jobid)
        for pname in self.jdl.content['used']:
            if pname in files.keys():
                if not os.path.isdir(upload_dir):
                    os.makedirs(upload_dir)
                f = files[pname]
                f.save(upload_dir + '/' + f.filename)
                logger.info('Input {} is a file and was downloaded ({})'.format(pname, f.filename))
                # Parameter value is set to the file name on server
                value = 'file://' + f.filename
                # value = f.filename
                self.parameters[pname] = {
                    'value': value,
                    'byref': True
                }
            elif pname in post:
                value = post[pname]
                logger.info('Input {} is a value : {}'.format(pname, value))
                # TODO: use url in jdl.used if set (replace $ID with value)
            else:
                logger.info('Input {} set by default'.format(pname))
                value = self.jdl.content['used'][pname]['default']
            self.parameters[pname] = {'value': value, 'byref': False}
        # Search parameters in POST
        for pname in self.jdl.content['parameters']:
            if pname not in self.parameters:
                # TODO: use JDL to check if value is valid
                ptype = self.jdl.content['parameters'][pname]['datatype']
                if 'anyURI' in ptype:
                    byref = True
                else:
                    byref = False
                if pname in post:
                    value = post[pname]
                else:
                    value = self.jdl.content['parameters'][pname]['default']
                self.parameters[pname] = {'value': value, 'byref': byref}
        # Upload files for multipart/form-data
        #for fname, f in files.iteritems():
        # Save to storage
        self.storage.save(self, save_attributes=True, save_parameters=True)


    # ----------
    # Method to set a job attribute or parameter
    # ----------


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
    # ----------


    def parameters_to_bash(self, separator='\n', get_files=False):
        """Make parameter file content for given job

        Returns:
            All parameters as a list of bash variables
            Dictionnary of files uploaded (from the 'form' or given as an 'URI')
        """
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        params = ['# Required parameters']
        files = {'URI': [], 'form': []}
        # Job parameters
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
        # Used
        params.append('# Used')
        for pname, pdict in self.jdl.content['used'].iteritems():
            if not pname in self.parameters:
                pvalue = pdict['default']
                if get_files:
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
            if not rname in self.parameters:
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
        xmlns_uris = {
            'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'
        }
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
        xmlns_uris = {
            'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'
        }
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

        xmlns_uris = {
            'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'
        }
        xml_job = ETree.Element('uws:job', attrib=xmlns_uris)
        add_sub_elt(xml_job, 'uws:jobId', self.jobid)
        add_sub_elt(xml_job, 'uws:phase', self.phase)
        add_sub_elt(xml_job, 'uws:executionDuration', self.execution_duration)
        add_sub_elt(xml_job, 'uws:quote', self.quote)
        add_sub_elt(xml_job, 'uws:error', self.error)
        add_sub_elt(xml_job, 'uws:creationTime', self.creation_time)
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
    # Metadata management
    # ----------


    def add_result_entry(self, rname, rfname, content_type):
        # TODO: Use an Entity Store
        url = '{}/get/result/{}/{}'.format(BASE_URL, self.jobid, rname)  # , rfname)
        self.results[rname] = {'url': url, 'content_type': content_type}
        logger.info('add {} file to results'.format(rfname))

    def add_results(self):
        # Get JDL to know expected job results
        if not self.jdl.content:
            self.jdl.read(self.jobname)
        # Check results and all links to db (maybe not all results listed in JDL have been created)
        for rname, r in self.jdl.content['results'].iteritems():
            rfname = self.get_result_filename(rname)
            rfpath = '{}/{}/results/{}'.format(JOBDATA_PATH, self.jobid, rfname)
            if os.path.isfile(rfpath):
                self.add_result_entry(rname, rfname, r['content_type'])
            else:
                logger.info('No result for {}'.format(rname))

    def add_logs(self):
        # Link job logs stdout and stderr (added as a result)
        rfdir = '{}/{}/results/'.format(JOBDATA_PATH, self.jobid)
        for rname in ['stdout', 'stderr']:
            rfname = rname + '.log'
            if os.path.isfile(rfdir + rfname):
                self.add_result_entry(rname, rfname, 'text/plain')
            else:
                logger.warning('File {} missing'.format(rfname))

    def add_provenance(self):
        # Create PROV files (added as a result)
        if GENERATE_PROV:
            rfdir = '{}/{}/results/'.format(JOBDATA_PATH, self.jobid)
            ptypes = ['json', 'xml', 'svg']
            content_types = {
                'json': 'application/json',
                'xml': 'text/xml',
                'svg': 'image/svg+xml'}
            try:
                pdoc = voprov.job2prov(self)
                voprov.prov2json(pdoc, rfdir + 'provenance.json')
                voprov.prov2xml(pdoc, rfdir + 'provenance.xml')
                voprov.prov2svg(pdoc, rfdir + 'provenance.svg')
            except Exception as e:
                logger.warning('ERROR in provenance files creation: ' + e.message)
            for ptype in ptypes:
                # PROV JSON
                rname = 'prov' + ptype
                rfname = 'provenance.' + ptype
                if os.path.isfile(rfdir + rfname):
                    self.add_result_entry(rname, rfname, content_types[ptype])
                else:
                    logger.warning('File {} missing'.format(rfname))


    # ----------
    # Actions on a job
    # ----------


    def start(self):
        """Start job

        Job can be started only if it is in PENDING state
        """
        # Test if status is PENDING as expected
        if self.phase == 'PENDING':
            pid = self.manager.start(self)
        else:
            raise UserWarning('Job {} is not in the PENDING state'.format(self.jobid))
        try:
            # Test if pid is an integer
            pid = int(pid)
        except ValueError:
            raise RuntimeError('Bad pid returned for job {}:\npid:\n{}'
                               ''.format(self.jobid, pid))
        self.pid = pid
        # No need to change times: job not started yet
        # now = dt.datetime.now()
        # duration = dt.timedelta(0, self.execution_duration)
        # destruction = dt.timedelta(DESTRUCTION_INTERVAL)
        # self.start_time = now.strftime(DT_FMT)
        # self.end_time = None  # (now + duration).strftime(DT_FMT)
        # self.destruction_time = (now + destruction).strftime(DT_FMT)
        # Change phase to QUEUED
        self.change_status('QUEUED')

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
        self.change_status('ABORTED', 'Job aborted by user ' + self.user.name)

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
        if self.phase in ['PENDING', 'QUEUED', 'EXECUTING', 'HELD', 'SUSPENDED', 'ERROR']:
            # Change phase
            now = dt.datetime.now()
            # logger.info('now={}'.format(now))
            # destruction = dt.timedelta(DESTRUCTION_INTERVAL)
            if new_phase not in ['QUEUED', 'HELD', 'SUSPENDED', 'EXECUTING', 'COMPLETED', 'ABORTED', 'ERROR']:
                raise UserWarning('Phase change not allowed: {} --> {}'.format(self.phase, new_phase))
            # Run case
            # cases[new_phase](self, error)
            # Set start_time
            if new_phase in ['QUEUED']:
                self.start_time = now.strftime(DT_FMT)
            # Set end_time
            if new_phase in ['COMPLETED', 'ABORTED', 'ERROR']:
                self.manager.get_jobdata(self)
                if self.phase != 'ERROR':
                    self.end_time = now.strftime(DT_FMT)
                # Add results, logs, provenance (if they exist...)
                self.add_results()
                self.add_logs()
                if new_phase in ['COMPLETED']:
                    self.add_provenance()
            if new_phase in ['ERROR']:
                # Set job.error or add
                if self.error:
                    self.error += '. ' + error
                else:
                    self.error = error
                # If phase is already ABORTED, keep it
                if self.phase == 'ABORTED':
                    new_phase = 'ABORTED'
            # Update phase
            previous_phase = self.phase
            self.phase = new_phase
            # Save job description
            # logger.info('end_time={}'.format(self.end_time))
            self.storage.save(self, save_results=True)
            # Send signal (e.g. if WAIT command expecting signal)
            change_status_signal = signal('job_status')
            result = change_status_signal.send('change_status', sig_jobid=self.jobid, sig_phase=self.phase)
            #logger.info('Signal sent for status change ({} --> {}). Results: \n{}'.format(previous_phase, self.phase, str(result)))
        else:
            raise UserWarning('Job {} cannot be updated to {} while in phase {}'
                              ''.format(self.jobid, new_phase, self.phase))


# -------------
# JobList class


class JobList(object):
    """JobList with attributes and function to fetch from storage and return as XML"""

    def __init__(self, jobname, user, phase=None, check_user=True):
        self.jobname = jobname
        self.user = user
        # Link to the storage, e.g. SQLiteStorage, see settings.py
        self.storage = storage.__dict__[STORAGE + 'JobStorage']()
        self.jobs = self.storage.get_list(self, phase=phase, check_user=check_user)

    def to_xml(self):
        """Returns the XML representation of jobs (uws:jobs)"""
        # xml_out = [
        #     '<?xml version="1.0" encoding="UTF-8"?>',
        #     '<uws:jobs ',
        #     'xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ',
        #     'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ',
        #     'xsi:schemaLocation="http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd" ',
        #     'xmlns:xlink="http://www.w3.org/1999/xlink">',
        # ]
        # for job in self.jobs:
        #     href = '{}/{}/{}'.format(BASE_URL, self.jobname, job['jobid'])
        #     xml_out.append('<uws:jobref id="{}" xlink:href="{}">'.format(job['jobid'], href))
        #     xml_out.append('<uws:phase>{}</uws:phase>'.format(job['phase']))
        #     xml_out.append('</uws:jobref>')
        # xml_out.append('</uws:jobs>')
        # return ''.join(xml_out)

        xmlns_uris = {
            'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.ivoa.net/xml/UWS/v1.0 http://ivoa.net/xml/UWS/UWS-v1.0.xsd'
        }
        xml_jobs = ETree.Element('uws:jobs', attrib=xmlns_uris)
        for job in self.jobs:
            href = '{}/{}/{}'.format(BASE_URL, self.jobname, job['jobid'])
            xml_job = ETree.SubElement(xml_jobs, 'uws:jobref', attrib={
                'id': job['jobid'],
                'xlink:href': href,
            })
            ETree.SubElement(xml_job, 'uws:phase').text = job['phase']
        return ETree.tostring(xml_jobs)


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
                html += '{} ({}): {} <br>'.format(str(rname), r['content_type'], r['url'])
        return html
