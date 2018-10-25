#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Defines classes for UWS objects job and job_list
"""

import shutil
import urllib.request, urllib.parse, urllib.error
import requests
import re
import datetime as dt
import xml.etree.ElementTree as ETree
import yaml
from blinker import signal
from . import uws_jdl
from . import storage
from . import managers
from .settings import *


# ---------
# Exceptions/Warnings


class JobAccessDenied(Exception):
    """User has no right to access job"""
    pass


class TooManyJobs(Exception):
    """User has no right to access job"""
    pass


class EntityAccessDenied(Exception):
    """User has no right to access job"""
    pass


# ---------
# Helper function


def is_downloadable(url):
    """
    Does the url contain a downloadable resource
    """
    h = requests.head(url, allow_redirects=True)
    header = h.headers
    content_type = header.get('content-type')
    if 'html' in content_type.lower():
        logger.warning('Fiund HTML page, nothing to download')
        return False
    content_length = header.get('content-length', None)
    if content_length and content_length > 2e8:  # 200 mb approx
        logger.warning('File is too large to be downloaded')
        return False
    return True


def get_filename_from_cd(cd):
    """
    Get filename from content-disposition
    """
    if not cd:
        return None
    fname = re.findall('filename=\"(.+)\"', cd)
    if len(fname) == 0:
        return None
    return fname[0]


# ---------
# User class


class User(object):
    """A user is defined by a name and a persistent ID (TOKEN) or token
    The TOKEN remains constant for a given user using a given client.
    Ideally it is a more general TOKEN set during the authentication (e.g with eduGain/Shibboleth).
    The user name/token can be sent via Basic access authentication
    """

    def __init__(self, name='anonymous', token='anonymous'):
        self.name = name
        self.token = token

    def __str__(self):
        return self.name

    def __eq__(self, other):
        """Override the default Equals behavior"""
        return self.name == other.name and self.token == other.token


special_users = [
    User(ADMIN_NAME, ADMIN_TOKEN),
    User('job_event', JOB_EVENT_TOKEN),
    User('maintenance', MAINTENANCE_TOKEN)
]


def check_admin(user):
    return user == User(ADMIN_NAME, ADMIN_TOKEN)


def check_permissions(job):
    """Check if user has rights to create/edit such a job, else raise JobAccessDenied"""
    if CHECK_PERMISSIONS:
        if job.user in special_users:
            # logger.debug('Permission granted for special user {} (job {}/{})'.format(job.user.name, job.jobname, job.jobid))
            pass
        else:
            if job.jobname:
                if not job.storage.has_access(job.user, job.jobname):
                    raise JobAccessDenied('User {} does not have permission to create/edit {} jobs'.format(job.user.name, job.jobname))
    # else:
    #    logger.debug('Permissions not checked for job {}/{}'.format(job.jobname, job.jobid))


def check_owner(job):
    """Check if user has rights to create/edit such a job, else raise JobAccessDenied"""
    if CHECK_OWNER:
        if job.user in special_users:
            pass
        else:
            if job.user == User(job.owner, job.owner_token):
                pass
            else:
                raise JobAccessDenied('User {} is not the owner of the job'.format(job.user.name))


def upper2underscore(inputstring):
    return ''.join('_' + char.lower() if char.isupper() else char for char in inputstring).lstrip('_')


# ---------
# Job class


class Job(object):
    """Job with UWS attributes and methods to create, set and show job information"""

    # Each Job contains:
    # • Exactly one Execution Phase.
    # • Exactly one Execution Duration.
    # • Exactly one Destruction Time
    # • Zero or one Quote.
    # • Exactly one Results List.
    # • Exactly one Owner.
    # • Zero or one Run Identifier.
    # • Zero or one Error.
    # In addition a job has a number of other properties (e.g. creationTime) which are set automatically
    # by the UWS and are not able to be directly manipulated by the client, hence are not represented
    # as separate object.

    def __init__(self, jobname, jobid, user,
                 get_attributes=True, get_parameters=False, get_results=False,
                 from_post=None, from_process_id=False,
                 run_check_owner=True):
        """Initialize from storage or from POST

        from_post should contain the request object if not None
        """
        # Job description
        self.jobname = jobname
        if from_process_id:
            # use process_id to restore jobname and jobid
            self.jobid = None
            self.process_id = jobid
        else:
            if not jobid:
                # Create new jobid
                jobid = JOB_ID_GEN()
            self.jobid = jobid
            self.process_id = None
        self.user = user
        # Link to the storage, e.g. SQLite, see settings.py
        # self.storage = storage.__dict__[STORAGE + 'JobStorage']()
        # logger.debug('Init storage for job {}'.format(self.jobid))
        self.storage = getattr(storage, STORAGE + 'JobStorage')()

        # Check if user has rights to create/edit such a job, else raise JobAccessDenied
        check_permissions(self)

        # Link to the job manager, e.g. SLURM, see settings.py
        # self.manager = managers.__dict__[MANAGER + 'Manager']()
        self.manager = getattr(managers, MANAGER + 'Manager')()
        # Prepare jdl attribute, see settings.py
        # self.jdl = uws_jdl.__dict__[JDL]()
        self.jdl = getattr(uws_jdl, JDL)()

        # Fill job attributes
        if from_post:
            # Check if max number of running jobs is not reached
            jobs = self.storage.get_list(self, phase=ACTIVE_PHASES, where_owner=True)
            if NJOBS_MAX and len(jobs) >= NJOBS_MAX:
                raise TooManyJobs('Maximum number of active jobs reached for {} ({})'.format(user.name, NJOBS_MAX))
            # Create a new PENDING job and save to storage
            now = dt.datetime.now()
            destruction = dt.timedelta(DESTRUCTION_INTERVAL)  # default interval for UWS server
            duration = dt.timedelta(0, EXECUTION_DURATION_DEF)  # default duration of 60s, from jdl ?
            self.phase = 'PENDING'
            self.quote = duration.total_seconds()
            self.execution_duration = duration.total_seconds()
            self.error = None
            self.creation_time = now.strftime(DT_FMT)
            self.start_time = None  # now.strftime(DT_FMT)
            self.end_time = None  # (now + duration).strftime(DT_FMT)
            self.destruction_time = (now + destruction).strftime(DT_FMT)
            self.owner = user.name
            self.owner_token = user.token
            self.run_id = None
            self.parameters = {}
            self.results = {}
            # Set parameters from POSTed info
            self.set_from_post(from_post.POST, from_post.files)

        elif get_attributes or get_parameters or get_results:
            # Get from storage
            self.storage.read(self,
                              get_attributes=get_attributes,
                              get_parameters=get_parameters,
                              get_results=get_results,
                              from_process_id=from_process_id)
            # Check if the user is the owner of the job, else raise JobAccessDenied
            if run_check_owner:
                check_owner(self)

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
            self.owner_token = None
            self.run_id = None
            self.parameters = {}
            self.results = {}

        if not self.jobname:
            logger.debug('Attribute jobname not given for jobid {}'.format(self.jobid))


    # ----------
    # Method to read job description from JDL file
    # ----------


    def get_result_filename(self, rname):
        """Get the filename corresponding to the result name"""
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
            fname = self.jdl.content['generated'][rname]['default']
        logger.debug('Result filename for {} is {}'.format(rname, fname))
        return fname


    # ----------
    # Method to get job attributes from storage or POST
    # ----------


    def set_from_post(self, post, files):
        """Set attributes and parameters from POST"""
        logger.debug('{}'.format(post.__dict__))
        logger.debug('{}'.format(files.keys()))
        # Read JDL
        self.jdl.read(self.jobname)
        # Pop UWS attributes keywords from POST or set by default
        self.execution_duration = self.jdl.content.get('executionDuration', EXECUTION_DURATION_DEF)
        # Pop internal attributes
        for pname in ['control_parameters', 'csrf_token']:
            if pname in post:
                post.pop(pname)
        for pname in CONTROL_PARAMETERS_KEYS:
            if pname in post:
                value = post.pop(pname)
                self.parameters[pname] = {
                    'value': value,
                    'byref': False,
                    'entity_id': None,
                }
                if pname in UWS_PARAMETERS:
                    pname = upper2underscore(pname.split('uws_')[-1])  # remove the prefix uws_ to update the class attribute
                    #self.parameters[pname] = {'value': value, 'byref': False}
                    setattr(self, pname, value)
        # Search input entities in POST/files
        upload_dir = os.path.join(UPLOADS_PATH, self.jobid)
        for pname in self.jdl.content.get('used', {}):
            entity = {}
            content_type = self.jdl.content['used'][pname].get('content_type', None)
            if pname in list(files.keys()):
                # 1/ Parameter is a file from the form
                post_p = post.pop(pname)
                f = files[pname]
                if not os.path.isdir(upload_dir):
                    os.makedirs(upload_dir)
                f.save(os.path.join(upload_dir, f.filename))
                # Parameter value is set to the file name on server (known to be in the uploads/<jobid> directory)
                value = 'file://' + f.filename
                # value = f.filename
                logger.info('Input "{}" is a file and was downloaded ({})'.format(pname, f.filename))
                # Check if file already exists in entity store (hash + ID in name or jobid) and add in Used table
                entity = self.storage.register_entity(
                    file_name=f.filename,
                    file_dir=upload_dir,
                    used_jobid=self.jobid,
                    used_role=pname,
                    owner=self.user.name,
                    content_type=content_type
                )
            else:
                # 2/ Parameter is a value, possibly an ID (set from post or by default)
                if pname in post:
                    # Get value from post
                    value = post.pop(pname)
                    logger.info('Input "{}" is a value (or an identifier): {}'.format(pname, value))
                else:
                    # Set value to its default
                    value = self.jdl.content['used'][pname]['default']
                    logger.info('Input "{}" set by default: {}'.format(pname, value))
                # 3/ Try to convert value/ID to a URL and upload
                url = self.jdl.content['used'][pname]['url']
                if url:
                    furl = url.replace('$ID', value)
                    # TODO: upload the file to upload dir
                    if furl != 'file://':
                        r = requests.get(furl, allow_redirects=True)
                        if r.status_code == 200:
                            cd = r.headers.get('content-disposition')
                            filename = get_filename_from_cd(cd)
                            if not os.path.isdir(upload_dir):
                                os.makedirs(upload_dir)
                            open(os.path.join(upload_dir, filename), 'wb').write(r.content)
                            # Parameter value is set to the file name on server
                            value = 'file://' + filename
                            logger.info('Input "{}" is a URL and was downloaded : {}'.format(pname, furl))
                            # TODO: check if file already exists in entity store (hash + ID in name or jobid)
                            entity = self.storage.register_entity(
                                file_name=filename,
                                file_dir=upload_dir,
                                used_jobid=self.jobid,
                                used_role=pname,
                                owner=self.user.name,
                                content_type=content_type
                            )
                        else:
                            logger.warning('Cannot upload URL for input "{}": {}'.format(pname, furl))
                # TODO: 4/ check if value is an ID that already exists in the entity store ? other attribute ?
                if not entity:
                    pass
            # Store Input entity in UWS parameters
            self.parameters[pname] = {
                'value': value,
                'byref': True,
                'entity_id': entity.get('entity_id', None),
            }
        # Search parameters in POST
        for pname in self.jdl.content.get('parameters', {}):
            if pname not in self.parameters:
                # TODO: use JDL to check if value is valid
                ptype = self.jdl.content['parameters'][pname]['datatype']
                if pname in post:
                    value = post.pop(pname)
                else:
                    value = self.jdl.content['parameters'][pname]['default']
                self.parameters[pname] = {
                    'value': value,
                    'byref': False,
                    'entity_id': False,
                }
        # Other POST parameters
        for pname in post:
            # Those parameters won't be used for job control, or stored as used entities, but they will be loaded
            # in the environment during execution
            if pname not in ['PHASE']:
                value = post[pname]
                self.parameters[pname] = {
                    'value': value,
                    'byref': False,
                    'entity_id': False,
                }
        # Upload files for multipart/form-data
        #for fname, f in files.iteritems():
        # Save to storage
        self.storage.save(self, save_attributes=True, save_parameters=True)


    # ----------
    # Method to set a job attribute or parameter
    # ----------


    def set_attribute(self, attr, value):
        """Set job attribute and save to storage"""
        if hasattr(self, attr):
            # self.__dict__[attr] = value
            setattr(self, attr, value)
            # self.save_description()
            self.storage.save(self, save_attributes=True, save_parameters=False, save_results=False)
        else:
            raise KeyError(attr)

    def set_parameter(self, pname, value):
        """Set job attribute and save to storage"""
        self.parameters[pname]['value'] = value
        #self.save_description()
        self.storage.save(self, save_attributes=False, save_parameters=pname, save_results=False)


    # ----------
    # Methods to export a job description
    # ----------


    def parameters_to_bash(self, separator='\n', get_files=False):
        """Make parameter file content for given job

        Returns:
            All parameters as a list of bash variables
            Dictionnary of files uploaded (from the 'form' or given as an 'URI')
        """
        self.jdl.read(self.jobname)
        params = ['# Required parameters']
        files = {'URI': [], 'form': []}
        # Job parameters
        for pname, pdict in self.parameters.items():
            pvalue = pdict['value']
            if get_files:
                # Prepare file upload and convert param value for files
                # Test if file is given as a URI, prefixed by http*
                if any(s in pvalue for s in ['http://', 'https://']):
                    files['URI'].append(pvalue)
                    pvalue = pvalue.split('/')[-1]
                # Test if file was uploaded from the form, and given the "file://" prefix (see self.set_from_post())
                if 'file://' in pvalue:
                    pvalue = pvalue.split('file://')[-1]
                    files['form'].append(pvalue)
            params.append(pname + '=\"' + pvalue + '\"')
        # Used
        params.append('# Used')
        for pname, pdict in self.jdl.content.get('used', {}).items():
            if not pname in self.parameters:
                pvalue = pdict['default']
                if get_files:
                    if any(s in pvalue for s in ['http://', 'https://']):
                        files['URI'].append(pvalue)
                        pvalue = pvalue.split('/')[-1]
                    # Test if file was uploaded from the form, and given the "file://" prefix (see self.set_from_post())
                    if 'file://' in pvalue:
                        pvalue = pvalue.split('file://')[-1]
                        files['form'].append(pvalue)
                params.append(pname + '=\"' + pvalue + '\"')
        # Results
        params.append('# Results')
        for rname, rdict in self.jdl.content.get('generated', {}).items():
            if not rname in self.parameters:
                rvalue = rdict['default']
                params.append(rname + '=\"' + rvalue + '\"')
        # Other parameters
        params.append('# Other parameters')
        for pname, pdict in self.jdl.content.get('parameters', {}).items():
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
        for pname, pdict in self.parameters.items():
            params.append('"{}": "{}"'.format(pname, pdict['value']))
        return '{' + ', '.join(params) + '}'

    def _parameters_to_xml_fill(self, xml_params):
        # Add each parameter that has a value
        for pname, pdict in self.parameters.items():
            if pdict['value']:
                value = urllib.parse.quote_plus(urllib.parse.unquote_plus(pdict['value']))
                by_ref = str(pdict['byref']).lower()
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
        for rname, r in self.results.items():
            if r['url']:
                attrib = {
                    'id': rname,
                    'xlink:href': r['url'],
                    'mime-type': r['content_type'] or 'text/plain',
                }
                ETree.SubElement(xml_results, 'uws:result', attrib=attrib)

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
        add_sub_elt(xml_job, 'uws:runId', self.run_id)
        add_sub_elt(xml_job, 'uws:ownerId', self.owner)
        add_sub_elt(xml_job, 'uws:phase', self.phase)
        add_sub_elt(xml_job, 'uws:creationTime', self.creation_time)
        add_sub_elt(xml_job, 'uws:startTime', self.start_time)
        add_sub_elt(xml_job, 'uws:endTime', self.end_time)
        add_sub_elt(xml_job, 'uws:quote', self.quote)
        add_sub_elt(xml_job, 'uws:executionDuration', self.execution_duration)
        add_sub_elt(xml_job, 'uws:destruction', self.destruction_time)
        xml_params = ETree.SubElement(xml_job, 'uws:parameters')
        self._parameters_to_xml_fill(xml_params)
        xml_results = ETree.SubElement(xml_job, 'uws:results')
        self._results_to_xml_fill(xml_results)
        add_sub_elt(xml_job, 'uws:errorSummary', self.error)
        xml_jobinfo = ETree.SubElement(xml_job, 'uws:jobInfo')
        # ETree.SubElement(xml_jobinfo, 'process_id').text = str(self.process_id)
        add_sub_elt(xml_jobinfo, 'process_id', str(self.process_id))
        # logger.debug(self.jobid)
        try:
            return ETree.tostring(xml_job)
        except:
            raise UserWarning('Cannot serialize job {}'.format(self.jobid))


    # ----------
    # Metadata management
    # ----------

    def add_result_entry(self, rid, url, content_type, entity_id):
        self.results[rid] = {'url': url, 'content_type': content_type, 'entity_id': entity_id}

    def add_results(self):
        # Read results.yml to know generated results (those that are located in the results directory)
        rf_name = os.path.join(JOBDATA_PATH, self.jobid, 'results.yml')
        now = dt.datetime.now()
        result_list = {}
        if os.path.isfile(rf_name):
            with open(rf_name, 'r') as rf:
                result_list = yaml.load(rf)
        for rname in result_list:
            rinfo = dict(result_list[rname])
            logger.debug(rinfo)
            entity = self.storage.register_entity(
                jobid = self.jobid,
                creation_time = now.strftime(DT_FMT),
                owner = self.owner,
                # result_name = rinfo['result_name'],
                # result_value = rinfo['result_value'],
                # hash = rinfo['hash'],
                # content_type = rinfo['content_type'],
                # file_name = rinfo['file_name'],
                # file_dir = rinfo['file_dir'],
                **rinfo,
            )
            rid = rinfo['result_name']
            if '*' in rinfo['result_value']:
                rid = rname
            self.add_result_entry(rid, entity['access_url'], entity['content_type'], entity['entity_id'])
            logger.info('Result added to job {}: {}'.format(self.jobid, rid))

        # access_url computed for UWS server (retrieve endpoint with entity_id)
        #                     or distant server (url given with $ID to replace by entity_id)

        # # Get JDL to know expected job results (but already done in copy_results() from Manager)
        # if not self.jdl.content:
        #     self.jdl.read(self.jobname)
        # # Check results and all links to db (maybe not all results listed in JDL have been created)
        # for rname, r in self.jdl.content['generated'].iteritems():
        #     rfname = self.get_result_filename(rname)
        #     rfpath = '{}/{}/{}'.format(RESULTS_PATH, self.jobid, rfname)
        #     if os.path.isfile(rfpath):
        #         self.add_result_entry(rname, rfname, r['content_type'])
        #     else:
        #         logger.info('No result for {}'.format(rname))

    def add_logs(self):
        # Link job logs stdout and stderr (added as a result)
        rfdir = '{}/{}/'.format(JOBDATA_PATH, self.jobid)
        for rname in ['stdout', 'stderr']:
            rfname = rname + '.log'
            if os.path.isfile(rfdir + rfname):
                url = '{}//rest/{}/{}/{}'.format(BASE_URL, self.jobname, self.jobid, rname)
                self.add_result_entry(rname, url, 'text/plain', None)
            else:
                logger.warning('Log file missing: {}'.format(rfname))

    def add_provenance(self):
        # Create PROV files (added as a result)
        if GENERATE_PROV:
            from . import provenance
            rfdir = '{}/{}/'.format(JOBDATA_PATH, self.jobid)
            ptypes = ['json', 'xml', 'svg']
            content_types = {
                'json': 'application/json',
                'xml': 'text/xml',
                'svg': 'image/svg+xml',
            }
            try:
                # TODO: check input entities and retrieve their provenance...
                pdoc = provenance.job2prov(self.jobid, self.user)
                provenance.prov2json(pdoc, rfdir + 'provenance.json')
                provenance.prov2xml(pdoc, rfdir + 'provenance.xml')
                provenance.prov2svg(pdoc, rfdir + 'provenance.svg')
            except Exception as e:
                logger.error('ERROR in provenance files creation: ' + str(e))
                raise
            for ptype in ptypes:
                # PROV JSON
                rname = 'prov' + ptype
                rfname = 'provenance.' + ptype
                if os.path.isfile(rfdir + rfname):
                    url = '{}//rest/{}/{}/prov{}'.format(BASE_URL, self.jobname, self.jobid, ptype)
                    self.add_result_entry(rname, url, content_types[ptype], None)
                else:
                    logger.warning('Provenance file missing: {}'.format(rfname))


    # ----------
    # Actions on a job
    # ----------

    def start(self):
        """Start job

        Job can be started only if it is in PENDING state
        """
        # Test if status is PENDING as expected
        if self.phase == 'PENDING':
            process_id = self.manager.start(self)
        else:
            raise UserWarning('Job {} is not in the PENDING state'.format(self.jobid))
        try:
            # Test if process_id is an integer
            process_id = int(process_id)
        except ValueError:
            raise RuntimeError('Bad process_id returned for job {}:\nprocess_id:\n{}'
                               ''.format(self.jobid, process_id))
        self.process_id = process_id
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
        uploads_dir = '{}/{}'.format(UPLOADS_PATH, self.jobid)
        if os.path.isdir(uploads_dir):
            shutil.rmtree(uploads_dir)
        # Remove jobdata files corresponding to jobid if needed
        jobdata_dir = '{}/{}'.format(JOBDATA_PATH, self.jobid)
        if os.path.isdir(jobdata_dir):
            shutil.rmtree(jobdata_dir)
        # Remove results files corresponding to jobid if needed
        results_dir = '{}/{}'.format(RESULTS_PATH, self.jobid)
        if os.path.isdir(results_dir):
            shutil.rmtree(results_dir)
        # Remove job and entities from storage
        # TODO: remove or keep entities ? may break the provenance...
        self.storage.remove_entity(jobid=self.jobid)
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
            # Set start_time
            if new_phase in ['QUEUED']:
                self.start_time = now.strftime(DT_FMT)
            if self.phase not in ['ERROR']:
                try:
                    # Get results, logs
                    if new_phase in ['COMPLETED', 'ABORTED', 'ERROR']:
                        self.end_time = now.strftime(DT_FMT)
                        self.manager.get_jobdata(self)
                        # Add results, logs, provenance (if they exist...) to job control db
                        self.add_results()
                        self.add_logs()
                    # Add provenance files
                    if new_phase in ['COMPLETED']:
                        # self.storage.read(self, get_parameters=True, get_results=True)
                        self.add_provenance()
                except Exception as e:
                    self.phase = 'ERROR'
                    error = 'Cannot get jobdata (or update db) for job {}'.format(self.jobid)
                    if self.error:
                        self.error += '. ' + error
                    else:
                        self.error = error
                    self.end_time = now.strftime(DT_FMT)
                    self.storage.save(self)
                    change_status_signal = signal('job_status')
                    result = change_status_signal.send('change_status', sig_jobid=self.jobid, sig_phase=self.phase)
                    raise
            # Increment error message is needed
            if new_phase in ['ERROR', 'ABORTED']:
                # Set job.error or add
                if self.error:
                    self.error += '. ' + error
                else:
                    self.error = error
                # If phase is already ABORTED, keep it
                if self.phase == 'ABORTED':
                    new_phase = 'ABORTED'
            # Set end_time
            if new_phase in ['COMPLETED', 'ABORTED']:
                self.end_time = now.strftime(DT_FMT)
            if new_phase == 'ERROR' and self.phase != 'ERROR':
                self.end_time = now.strftime(DT_FMT)
            # Update phase
            previous_phase = self.phase
            self.phase = new_phase
            # Save job description
            self.storage.save(self)
            # Send signal (e.g. if WAIT command expecting signal)
            change_status_signal = signal('job_status')
            result = change_status_signal.send('change_status', sig_jobid=self.jobid, sig_phase=self.phase)
            # logger.debug('Signal sent for status change ({} --> {}). Results: \n{}'.format(previous_phase, self.phase, str(result)))
        else:
            raise UserWarning('Job {} cannot be updated to {} while in phase {}'
                              ''.format(self.jobid, new_phase, self.phase))


# -------------
# JobList class


class JobList(object):
    """JobList with attributes and function to fetch from storage and return as XML"""

    def __init__(self, jobname, user, phase=None, after=None, last=None, where_owner=True):
        self.jobname = jobname
        self.jobid = 'joblist'
        self.user = user
        # Link to the storage, e.g. SQLiteStorage, see settings.py
        # logger.debug('Init storage for joblist')
        self.storage = getattr(storage, STORAGE + 'JobStorage')()

        # Check if user has rights to create/edit such a job, else raise JobAccessDenied
        check_permissions(self)

        # Check if user is admin, then get all jobs
        if check_admin(user):
            where_owner = False
            #logger.debug('User is the admin: list all jobs')

        self.jobs = self.storage.get_list(self, phase=phase, after=after, last=last, where_owner=where_owner)

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
            ETree.SubElement(xml_job, 'uws:runId').text = job['run_id']
            ETree.SubElement(xml_job, 'uws:ownerId').text = job['owner']
            ETree.SubElement(xml_job, 'uws:creationTime').text = job['creation_time']
        try:
            return ETree.tostring(xml_jobs)
        except:
            raise UserWarning('Cannot serialize joblist')

    def to_html(self):
        """Returns the HTML representation of jobs"""
        html = ''
        for row in self.jobs:
            # Job ID
            jobid = row['jobid']
            job = Job(self.jobname, jobid, self.user, get_attributes=True, get_parameters=True, get_results=True)
            html += '<h3>Job ' + jobid + '</h3>'
            for k in JOB_ATTRIBUTES:
                html += k + ' = ' + str(getattr(job, k)) + '<br>'
            # Parameters
            html += '<strong>Parameters:</strong><br>'
            for pname, p in job.parameters.items():
                html += pname + ' = ' + p['value'] + '<br>'
            # Results
            html += '<strong>Results</strong><br>'
            for rname, r in job.results.items():
                html += '{} ({}): {} <br>'.format(str(rname), r['content_type'], r['url'])
        return html
