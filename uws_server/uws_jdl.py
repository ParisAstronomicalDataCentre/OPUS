#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Interfaces between UWS server and job description
"""

import collections
import inspect
import copy
import json
import yaml
import lxml.etree as ETree
from .settings import *


# ---------
# jdl.content structure (class or dict?)

# job.jobname
'''
jdl.content = {
    'name': 'test',
    'annotation': 'test annotation',
    'version': '1.2',
    'group': '',
    'type': '',
    'subtype': '',
    'doculink': '',                    # 'url' --> 'doculink'
    'contact_name': 'contact name',
    'contact_email': 'contact@email.com',
    'parameters': {},
    'generated': {},
    'used': {},                        # add
    'executionduration': 1,
    'quote': 1,
}
parameters[pname] = {
    'type': p.get('type'),             # --> should be changed to 'datatype'
    'required': p.get('required'),     # type="no_query" in VOTable
    'default': p.get('default'),       # value in VOTable
    'unit': p.get('default'),          # add
    'ucd': p.get('default'),           # add
    'utype': p.get('default'),         # add
    'min': p.get('default'),           # add
    'max': p.get('default'),           # add
    'options': p.get('default'),       # add
    'annotation': list(p)[0].text,
}
used[pname] = {                        # add!
    'default': r.get('default'),
    'content_type': p.get('type'),     # xtype in VOTable (?)
    'annotation': list(r)[0].text,
}
generated[rname] = {
    'default': r.get('default'),
    'content_type': r.get('content_type'),
    'annotation': list(r)[0].text,
}
'''

# ---------
# Job Description Language


class JDLFile(object):
    """
    Manage job description. This class defines required functions executed
    by the UWS server: save(), read().
    """
    content = dict(
        control_parameters=CONTROL_PARAMETERS,
        control_parameters_keys=CONTROL_PARAMETERS_KEYS,
    )
    extension = ''
    jdl_path = '.'
    scripts_path = '.'

    def _get_filename(self, jobname, jobid=None):
        fn = '{}/{}{}'.format(self.jdl_path, jobname, self.extension)
        if jobid:
            fn_jobid = '{}/{}/{}{}'.format(JOBDATA_PATH, jobid, jobname, self.extension)
            if os.path.isfile(fn_jobid):
                logger.info('Loading JDL attached to job: {} {}'.format(jobname, jobid))
                fn = fn_jobid
        # logger.info('JDL filename: ' + fn)
        return fn

    def save(self, jobname):
        """Save job description to file"""
        pass

    def read(self, jobname):
        """Read job description from file"""
        pass

    def valid_xml_char_ordinal(self, c):
        codepoint = ord(c)
        # conditions ordered by presumed frequency
        return (
            0x20 <= codepoint <= 0xD7FF or
            codepoint in (0x9, 0xA, 0xD) or
            0xE000 <= codepoint <= 0xFFFD or
            0x10000 <= codepoint <= 0x10FFFF
            )

    def save_script(self, jobname, script):
        script_fname = '{}/{}.sh'.format(self.scripts_path, jobname)
        with open(script_fname, 'w') as f:
            f.write(script.replace('\r', ''))
            logger.info('Job script saved: ' + script_fname)

    def set_from_post(self, post):
        logger.debug(post.__dict__)
        # Read form
        keys = list(post.keys())
        jobname = post.get('name').split('/')[-1]
        # Create parameters dict
        params = collections.OrderedDict()
        iparam = 1
        while 'param_name_' + str(iparam) in keys:
            pname = post.get('param_name_' + str(iparam), '')
            if pname:
                params[pname] = {
                    'datatype': post.get('param_datatype_' + str(iparam), ''),
                    'default': post.get('param_default_' + str(iparam), ''),
                    'required': (post.get('param_required_' + str(iparam), '') == 'on'),
                    'annotation': post.get('param_annotation_' + str(iparam), ''),
                }
                poptions = post.get('param_options_' + str(iparam), '')
                if poptions:
                    params[pname]['options'] = poptions
                patts = post.get('param_attributes_' + str(iparam), '')
                if patts:
                    for patt in patts.split(' '):
                        if '=' in patt:
                            pattk, pattv = patt.split('=')
                            params[pname][pattk] = pattv
            iparam += 1
        # Create used dict
        used = collections.OrderedDict()
        iused = 1
        while 'used_name_' + str(iused) in keys:
            pname = post.get('used_name_' + str(iused), '')
            if pname:
                ptype = post.get('used_type_' + str(iused), '')
                # TODO: do a getall for all options
                pisfile = post.get('used_isfile_' + str(iused), '')
                purl = post.get('used_url_' + str(iused), '')
                if pisfile == 'File':
                    purl = 'file://$ID'.format(pname)
                used[pname] = {
                    'content_type': ptype,  # ', '.join(ptype),
                    'multiplicity': post.get('used_multiplicity_' + str(iused), ''),
                    'default': post.get('used_default_' + str(iused), ''),
                    'annotation': post.get('used_annotation_' + str(iused), ''),
                    'url': purl,
                }
            iused += 1
        # Create results dict
        results = collections.OrderedDict()
        iresult = 1
        while 'generated_name_' + str(iresult) in keys:
            rname = post.get('generated_name_' + str(iresult), '')
            if rname:
                results[rname] = {
                    'content_type': post.get('generated_type_' + str(iresult), ''),
                    'multiplicity': post.get('used_multiplicity_' + str(iresult), ''),
                    'default': post.get('generated_default_' + str(iresult), ''),
                    'annotation': post.get('generated_annotation_' + str(iresult), ''),
                }
                results.move_to_end(rname)
            iresult += 1
        # Create job.content structure
        self.content.update({
            'name': jobname,
            'annotation': post.get('annotation', jobname),
            #'description': post.get('description'),
            'doculink': post.get('doculink', ''),
            'url': post.get('url', ''),
            'group': post.get('group', ''),
            'type': post.get('type', ''),
            'subtype': post.get('subtype', ''),
            'version': post.get('version', ''),
            'contact_name': post.get('contact_name', ''),
            'contact_email': post.get('contact_email', ''),
            'parameters': params,
            'generated': results,
            'used': used,
            'executionDuration': post.get('executionDuration', EXECUTION_DURATION_DEF),
            'quote': post.get('quote', ''),
            'script': post.get('script', ''),
        })


class JSONFile(JDLFile):

    def __init__(self, jdl_path=JDL_PATH, scripts_path=SCRIPTS_PATH):
        self.extension = '.json'
        self.jdl_path = os.path.join(jdl_path, 'json')
        self.scripts_path = scripts_path

    def save(self, jobname):
        """Save job description to file"""
        raw_jobname = jobname.split('/')[-1]  # remove new/ prefix
        js = json.dumps(self.content, indent=4)
        jdl_fname = self._get_filename(jobname)
        with open(jdl_fname, 'w') as f:
            f.write(js)
            logger.info('JSON saved: ' + jdl_fname)

    def read(self, jobname):
        """Read job description from file"""
        raw_jobname = jobname.split('/')[-1]  # remove new/ prefix
        fname = self._get_filename(jobname)
        with open(fname, 'r') as f:
            #self.content = json.load(f)
            self.content.update(yaml.safe_load(f))


class VOTFile(JDLFile):

    datatype_vo2xs = {
        "boolean": 'xs:boolean',
        "unsignedByte": 'xs:unsignedByte',
        "short": 'xs:short',
        "int": 'xs:integer',
        "long": 'xs:long',
        "char": 'xs:string',
        "float": 'xs:float',
        "double": 'xs:double'
    }
    datatype_xs2vo = {
        "xs:boolean": 'boolean',
        "xs:unsignedByte": 'unsignedByte',
        "xs:short": 'short',
        "xs:int": 'int',
        "xs:integer": 'int',
        "xs:long": 'long',
        "xs:string": 'char',
        "xs:float": 'float',
        "xs:double": 'double',
        'xs:anyURI': 'char',
        'file': 'file'
    }

    def __init__(self, jdl_path=JDL_PATH, scripts_path=SCRIPTS_PATH):
        self.extension = '_vot.xml'
        self.jdl_path = os.path.join(jdl_path, 'votable')
        self.scripts_path = scripts_path
        self.xmlns_uris = {
            'xmlns': 'http://www.ivoa.net/xml/VOTable/v1.3',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation':
                'http://www.ivoa.net/xml/VOTable/v1.3 http://www.ivoa.net/xml/VOTable/v1.3',
        }

    def save(self, jobname):
        """Save job description to VOTable file"""
        raw_jobname = jobname.split('/')[-1]  # remove new/ prefix
        # VOTable root
        xmlns = self.xmlns_uris['xmlns']
        xsi = self.xmlns_uris['xmlns:xsi']
        jdl_tree = ETree.Element('VOTABLE', attrib={
            'version': '1.3',
            '{' + xsi + '}schemaLocation':
                'http://www.ivoa.net/xml/VOTable/v1.3 http://www.ivoa.net/xml/VOTable/v1.3',
        }, nsmap={'xsi': xsi, None: xmlns})
        resource = ETree.SubElement(jdl_tree, 'RESOURCE', attrib={
            'ID': raw_jobname,
            'name': raw_jobname,
            'type': "meta",
            'utype': "voprov:ActivityDescription"
        })
        # Job attributes
        if self.content['annotation']:
            ETree.SubElement(resource, 'DESCRIPTION').text = self.content['annotation']  # .decode() # not needed in Python 3
        # TODO: automatic list of attributes from jdl.content
        for key in ['doculink', 'type', 'subtype', 'version']:
            #'<PARAM name="{key}" datatype="char" arraysize="*" value="{value}" utype="voprov:ActivityDescription.{key}"/>'.format(key=key, value=self.content.get(key, '')))
            ETree.SubElement(resource, 'PARAM', attrib={
                'name': key,
                'value': str(self.content.get(key, '')),
                'arraysize': "*",
                'datatype': "char",
                'utype': 'voprov:ActivityDescription.{}'.format(key),
            })
        for key in ['name', 'email']:
            ETree.SubElement(resource, 'PARAM', attrib={
                'name': 'contact_' + key,
                'value': self.content.get('contact_{}'.format(key), ''),
                'arraysize': "*",
                'datatype': "char",
                'utype': 'voprov:Agent.{}'.format(key),
            })
        for key in ['executionDuration', 'quote']:
            ETree.SubElement(resource, 'PARAM', attrib={
                'name': key,
                'value': self.content.get(key, 1),
                'datatype': "int",
                'utype': 'uws:Job.{}'.format(key),
            })
        # Insert groups
        group_params = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "InputParams",
        })
        group_used = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "Used",
        })
        group_generated = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "Generated",
        })
        # Prepare InputParams group
        if 'parameters' in self.content:
            for pname, p in self.content['parameters'].items():
                param_attrib = {
                    'ID': pname,
                    'name': pname,
                    'datatype': self.datatype_xs2vo[p['datatype']],
                    'value': p.get('default'),
                }
                if param_attrib['datatype'] == 'file':
                    param_attrib['xtype'] = 'application/octet-stream'
                    param_attrib['datatype'] = 'char'
                if param_attrib['datatype'] == 'char':
                    param_attrib['arraysize'] = '*'
                if str(p['required']).lower() == 'false' :
                    param_attrib['type'] = 'no_query'
                param = ETree.Element('PARAM', attrib=param_attrib)
                pdesc = p.get('annotation', '')
                # .encode(encoding='utf-8', errors='ignore')
                # pdesc_clean = ''.join(c for c in pdesc if self.valid_xml_char_ordinal(c))
                # logger.debug(pdesc)
                # logger.debug(pdesc_clean)
                ETree.SubElement(param, 'DESCRIPTION').text = pdesc
                if p.get('min', False) or p.get('max', False) or p.get('options', False):
                    values = ETree.SubElement(param, 'VALUES')
                    if p.get('min', False):
                        ETree.SubElement(values, 'MIN', attrib={'value': p['min']})
                    if p.get('max', False):
                        ETree.SubElement(values, 'MAX', attrib={'value': p['max']})
                    if p.get('options', False):
                        for o in p['options'].split(','):
                            ETree.SubElement(values, 'OPTION', attrib={'value': o})
                group_params.append(param)
        # Prepare used block
        used_attr = [
            'role',
            'multiplicity',
            'default',
            'content_type',
            'url',
        ]
        used_utypes = {
            'role': 'voprov:UsedDescription.role',
            'multiplicity': 'voprov:UsedDescription.multiplicity',
            'default': 'voprov:Entity.id',
            'content_type': 'voprov:EntityDescription.content_type',
            'url': 'voprov:EntityDescription.url',
        }
        if 'used' in self.content:
            for pname, pdict in self.content['used'].items():
                attrib={
                    'name': pname,
                    'utype': 'voprov:UsedDescription',
                }
                if pname in self.content['parameters']:
                    attrib['ref'] = pname
                used = ETree.Element('GROUP', attrib=attrib)
                ETree.SubElement(used, 'DESCRIPTION').text = pdict.get('annotation', '')
                for edattr in used_attr:
                    ETree.SubElement(used, 'PARAM', attrib={
                        'name': edattr,
                        'value': pdict.get(edattr, ''),
                        'arraysize': "*",
                        'datatype': "char",
                        'utype': used_utypes.get(edattr, ''),
                    })
                group_used.append(used)
        # Prepare results block
        gen_attr = [
            'role',
            'multiplicity',
            'default',
            'content_type'
        ]
        gen_utypes = {
            'role': 'voprov:WasGeneratedByDescription.role',
            'multiplicity': 'voprov:WasGeneratedByDescription.multiplicity',
            'default': 'voprov:Entity.id',
            'content_type': 'voprov:EntityDescription.content_type',
            'url': 'voprov:EntityDescription.url',
        }
        if 'generated' in self.content:
            for rname, rdict in self.content['generated'].items():
                attrib={
                    'name': rname,
                    'utype': 'voprov:WasGeneratedBy',
                }
                if rname in self.content['parameters']:
                    attrib['ref'] = rname
                result = ETree.Element('GROUP', attrib=attrib)
                ETree.SubElement(result, 'DESCRIPTION').text = rdict.get('annotation', '')
                for edattr in gen_attr:
                    ETree.SubElement(result, 'PARAM', attrib={
                        'name': edattr,
                        'value': rdict.get(edattr, ''),
                        'arraysize': "*",
                        'datatype': "char",
                        'utype': gen_utypes.get(edattr, ''),
                    })
                group_generated.append(result)
        # Write file
        jdl_content = ETree.tostring(jdl_tree, pretty_print=True)
        jdl_fname = self._get_filename(jobname)
        with open(jdl_fname, 'wb') as f:
            f.write(jdl_content)
            logger.info('JDL saved as VOTable: ' + jdl_fname)

    def read(self, jobname, jobid=None):
        """Read job description from VOTable file"""
        raw_jobname = jobname.split('/')[-1]  # remove new/ prefix
        fname = self._get_filename(jobname, jobid=jobid)
        # '{}/{}{}'.format(JDL_PATH, job.jobname, self.extension)
        groups = {
            'InputParams': 'parameters',
            'Used': 'used',
            'Generated': 'generated'
        }
        try:
            with open(fname, 'r') as f:
                jdl_string = f.read()
            #print jdl_string
            jdl_tree = ETree.fromstring(jdl_string)
            #print jdl_tree
            # Get default namespace
            xmlns = '{' + jdl_tree.nsmap[None] + '}'
            #print xmlns
            # Read parameters description
            resource_block = jdl_tree.find(".//{}RESOURCE[@ID='{}']".format(xmlns, raw_jobname))
            #print resource_block
            job_def = {
                'name': resource_block.get('name'),
                'parameters': collections.OrderedDict(),
                'generated': collections.OrderedDict(),
                'used': collections.OrderedDict()
            }
            for elt in resource_block.getchildren():

                if elt.tag == '{}DESCRIPTION'.format(xmlns):
                    job_def['annotation'] = elt.text
                    #print elt.text
                if elt.tag == '{}LINK'.format(xmlns):
                    job_def['doculink'] = elt.get('href')
                if elt.tag == '{}PARAM'.format(xmlns):
                    # TODO: set datatype of value in the dictionary?
                    #print elt.get('name'), elt.get('value')
                    job_def[elt.get('name')] = elt.get('value', '')
                if elt.tag == '{}GROUP'.format(xmlns):
                    group = groups[elt.get('name')]
                    #print group
                    order = 0
                    keys = []
                    if group == 'parameters':
                        for p in elt:
                            if p.tag == '{}PARAM'.format(xmlns):
                                order += 1
                                name = p.get('name')
                                keys.append(name)
                                #print name, p.get('datatype', 'char')
                                pdatatype = p.get('datatype', 'char')
                                pxtype = p.get('xtype', None)
                                if pxtype == 'application/octet-stream':
                                    pdatatype = 'file'
                                else:
                                    pdatatype = self.datatype_vo2xs[pdatatype]
                                prequired = 'true'
                                if p.get('type') == 'no_query':    # type="no_query" in VOTable
                                    prequired = 'false'
                                item = {
                                    'datatype': pdatatype,
                                    'required': prequired,
                                    'default': p.get('value'),
                                    'unit': p.get('unit', ''),
                                    'ucd': p.get('ucd', ''),
                                    'utype': p.get('utype', ''),
                                }
                                for pp in p:
                                    if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                        item['annotation'] = pp.text
                                    if pp.tag == '{}VALUES'.format(xmlns):
                                        options = []
                                        for ppp in pp:
                                            if ppp.tag == '{}MIN'.format(xmlns):
                                                item['min'] = ppp.get('value')
                                            if ppp.tag == '{}MAX'.format(xmlns):
                                                item['max'] = ppp.get('value')
                                            if ppp.tag == '{}OPTION'.format(xmlns):
                                                options.append(ppp.get('value'))
                                        item['options'] = ','.join(options)
                                job_def[group][name] = item
                    if group == 'used':
                        for p in elt:
                            order += 1
                            name = p.get('name')
                            keys.append(name)
                            ref = p.get('ref')
                            item = {
                                'datatype': 'xs:string',  # may be changed below
                                'annotation': '',         # filled below
                                'url': '',                # default to ''
                            }
                            if ref:
                                item['datatype'] = job_def.get('parameters').get(ref).get('datatype', item['datatype'])
                                item['default'] = job_def.get('parameters').get(ref).get('default')
                                item['annotation'] = job_def.get('parameters').get(ref).get('annotation', item['annotation'])
                            for pp in p:
                                if pp.tag == '{}PARAM'.format(xmlns):
                                    if pp.get('name'):
                                        item[pp.get('name')] = pp.get('value')
                                if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                    item['annotation'] = pp.text
                                if pp.tag == '{}LINK'.format(xmlns):
                                    purl = pp.get('href')
                                    item['url'] = purl
                                    if 'file://' in purl:
                                        item['datatype'] = 'file'
                            job_def[group][name] = item
                    if group == 'generated':
                        for p in elt:
                            order += 1
                            name = p.get('name')
                            keys.append(name)
                            ref = p.get('ref')
                            item = {
                                'annotation': '',  # filled below
                            }
                            if ref:
                                item['default'] = job_def.get('parameters').get(ref).get('default')
                                item['annotation'] = job_def.get('parameters').get(ref).get('annotation')
                            for pp in p:
                                if pp.tag == '{}PARAM'.format(xmlns):
                                    if pp.get('name'):
                                        item[pp.get('name')] = pp.get('value')
                                if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                    item['annotation'] = pp.text
                            job_def[group][name] = item
                    job_def[group + '_keys'] = keys
            # Log votable access
            # frame, filename, line_number, function_name, lines, index = inspect.stack()[1]
            # logger.debug('VOTable read at {} ({}:{}): {}'.format(function_name, filename, line_number, fname))
        except IOError:
            # if file does not exist, continue and return an empty dict
            logger.debug('VOTable not found for job {}'.format(jobname))
            raise UserWarning('VOTable not found for job {}'.format(jobname))
        except Exception as e:
            logger.error('{}'.format(e))
            raise
            # return {}
        self.content.update(job_def)

    def save_old(self, jobname):
        """Save job description to VOTable file"""
        raw_jobname = jobname.split('/')[-1]  # remove new/ prefix
        # VOTable root
        xmlns = self.xmlns_uris['xmlns']
        xsi = self.xmlns_uris['xmlns:xsi']
        jdl_tree = ETree.Element('VOTABLE', attrib={
            'version': '1.3',
            '{' + xsi + '}schemaLocation':
                'http://www.ivoa.net/xml/VOTable/v1.3 http://www.ivoa.net/xml/VOTable/v1.3',
        }, nsmap={'xsi': xsi, None: xmlns})
        resource = ETree.SubElement(jdl_tree, 'RESOURCE', attrib={
            'ID': raw_jobname,
            'name': raw_jobname,
            'type': "meta",
            'utype': "voprov:ActivityDescription"
        })
        # Job attributes
        if self.content['annotation']:
            ETree.SubElement(resource, 'DESCRIPTION').text = self.content['annotation']  # .decode()
        # TODO: automatic list of attributes from jdl.content
        job_attr = []
        for key in ['annotation', 'doculink', 'type', 'subtype', 'version']:
            job_attr.append('<PARAM name="{key}" datatype="char" arraysize="*" value="{value}" utype="voprov:ActivityDescription.{key}"/>'.format(key=key, value=self.content.get(key, '')))
        #     ,
        #     '<PARAM name="subtype" datatype="char" arraysize="*" value="{}" utype="voprov:ActivityDescription.subtype"/>'.format(self.content.get('job_subtype', '')),
        #     '<PARAM name="annotation" datatype="char" arraysize="*" value="{}" utype="voprov:ActivityDescription.annotation"/>'.format(self.content.get('annotation', raw_jobname)),
        #     '<PARAM name="version" datatype="float" value="{}" utype="voprov:ActivityDescription.version"/>'.format(self.content.get('version', '')),
        #     '<PARAM name="doculink" datatype="float" value="{}" utype="voprov:ActivityDescription.doculink"/>'.format(self.content.get('doculink', '')),
        job_attr.append('<PARAM name="contact_name" datatype="char" arraysize="*" value="{}" utype="voprov:Agent.name"/>'.format(self.content.get('contact_name', '')))
        job_attr.append('<PARAM name="contact_email" datatype="char" arraysize="*" value="{}" utype="voprov:Agent.email"/>'.format(self.content.get('contact_email', '')))
        job_attr.append('<PARAM name="executionduration" datatype="int" value="{}" utype="uws:Job.executionduration"/>'.format(self.content.get('executionduration', '1')))
        job_attr.append('<PARAM name="quote" datatype="int" value="{}" utype="uws:Job.quote"/>'.format(self.content.get('quote', '1')))

        for attr in job_attr:
            resource.append(ETree.fromstring(attr))
        # Insert groups
        group_params = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "InputParams",
            'utype': "voprov:Parameter",
        })
        group_used = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "Used",
            'utype': "voprov:Used",
        })
        group_generated = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "Generated",
            'utype': "voprov:WasGeneratedBy",
        })
        # Prepare InputParams group
        if 'parameters' in self.content:
            for pname, p in self.content['parameters'].items():
                param_attrib = {
                    'ID': pname,
                    'name': pname,
                    'datatype': self.datatype_xs2vo[p['datatype']],
                    'value': p.get('default'),
                }
                if param_attrib['datatype'] == 'file':
                    param_attrib['xtype'] = 'application/octet-stream'
                    param_attrib['datatype'] = 'char'
                if param_attrib['datatype'] == 'char':
                    param_attrib['arraysize'] = '*'
                if str(p['required']).lower() == 'false' :
                    param_attrib['type'] = 'no_query'
    #                'required': str(p['required']),
    #                'content_type': 'text/plain'
                param = ETree.Element('PARAM', attrib=param_attrib)
                pdesc = p.get('annotation', '')
                  # .encode(encoding='utf-8', errors='ignore')
                #pdesc_clean = ''.join(c for c in pdesc if self.valid_xml_char_ordinal(c))
                #logger.debug(pdesc)
                #logger.debug(pdesc_clean)
                ETree.SubElement(param, 'DESCRIPTION').text = pdesc
                if p.get('min', False) or p.get('max', False) or p.get('options', False):
                    values = ETree.SubElement(param, 'VALUES')
                    if p.get('min', False):
                        ETree.SubElement(values, 'MIN', attrib={'value': p['min']})
                    if p.get('max', False):
                        ETree.SubElement(values, 'MAX', attrib={'value': p['max']})
                    if p.get('options', False):
                        for o in p['options'].split(','):
                            ETree.SubElement(values, 'OPTION', attrib={'value': o})
                group_params.append(param)
        # Prepare used block
        if 'used' in self.content:
            for pname, p in self.content['used'].items():
                attrib={
                    'name': pname,
                    'datatype': 'char',
                    'arraysize': '*',
                    'value': p.get('default'),
                    'xtype': p.get('content_type'),
                    'utype': 'voprov:Entity',
                }
                if pname in self.content['parameters']:
                    attrib['ref'] = pname
                used = ETree.Element('PARAM', attrib=attrib)
                url_attrib = {
                    'content-role': 'location',
                    'href': p.get('url'),
                }
                ETree.SubElement(used, 'LINK', attrib=url_attrib)
                ETree.SubElement(used, 'DESCRIPTION').text = p.get('annotation', '')
                group_used.append(used)
        # Prepare results block
        if 'generated' in self.content:
            for rname, r in self.content['generated'].items():
                attrib={
                    'name': rname,
                    'datatype': 'char',
                    'arraysize': '*',
                    'value': r['default'],
                    'xtype': r['content_type'],
                    'utype': 'voprov:Entity',
                }
                if rname in self.content['parameters']:
                    attrib['ref'] = rname
                result = ETree.Element('PARAM', attrib=attrib)
                ETree.SubElement(result, 'DESCRIPTION').text = r.get('annotation', '')
                group_generated.append(result)
        # Write file
        jdl_content = ETree.tostring(jdl_tree, pretty_print=True)
        jdl_fname = self._get_filename(jobname)
        with open(jdl_fname, 'w') as f:
            f.write(jdl_content)
            logger.info('JDL saved as VOTable: ' + jdl_fname)

    def read_old(self, jobname):
        """Read job description from VOTable file"""
        raw_jobname = jobname.split('/')[-1]  # remove new/ prefix
        fname = self._get_filename(jobname)
        # '{}/{}{}'.format(JDL_PATH, job.jobname, self.extension)
        groups = {
            'InputParams': 'parameters',
            'Used': 'used',
            'Generated': 'generated'
        }
        try:
            with open(fname, 'r') as f:
                jdl_string = f.read()
            #print jdl_string
            jdl_tree = ETree.fromstring(jdl_string)
            #print jdl_tree
            # Get default namespace
            xmlns = '{' + jdl_tree.nsmap[None] + '}'
            #print xmlns
            # Read parameters description
            resource_block = jdl_tree.find(".//{}RESOURCE[@ID='{}']".format(xmlns, raw_jobname))
            #print resource_block
            job_def = {
                'name': resource_block.get('name'),
                'parameters': collections.OrderedDict(),
                'generated': collections.OrderedDict(),
                'used': collections.OrderedDict()
            }
            for elt in resource_block.getchildren():

                if elt.tag == '{}DESCRIPTION'.format(xmlns):
                    job_def['annotation'] = elt.text
                    #print elt.text
                if elt.tag == '{}LINK'.format(xmlns):
                    job_def['doculink'] = elt.get('href')
                if elt.tag == '{}PARAM'.format(xmlns):
                    # TODO: set datatype of value in the dictionary?
                    #print elt.get('name'), elt.get('value')
                    job_def[elt.get('name')] = elt.get('value', '')
                if elt.tag == '{}GROUP'.format(xmlns):
                    group = groups[elt.get('name')]
                    #print group
                    order = 0
                    keys = []
                    if group == 'parameters':
                        for p in elt:
                            if p.tag == '{}PARAM'.format(xmlns):
                                order += 1
                                name = p.get('name')
                                keys.append(name)
                                #print name, p.get('datatype', 'char')
                                pdatatype = p.get('datatype', 'char')
                                pxtype = p.get('xtype', None)
                                if pxtype == 'application/octet-stream':
                                    pdatatype = 'file'
                                else:
                                    pdatatype = self.datatype_vo2xs[pdatatype]
                                prequired = 'true'
                                if p.get('type') == 'no_query':    # type="no_query" in VOTable
                                    prequired = 'false'
                                item = {
                                    'datatype': pdatatype,
                                    'required': prequired,
                                    'default': p.get('value'),
                                    'unit': p.get('unit', ''),
                                    'ucd': p.get('ucd', ''),
                                    'utype': p.get('utype', ''),
                                }
                                for pp in p:
                                    if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                        item['annotation'] = pp.text
                                    if pp.tag == '{}VALUES'.format(xmlns):
                                        options = []
                                        for ppp in pp:
                                            if ppp.tag == '{}MIN'.format(xmlns):
                                                item['min'] = ppp.get('value')
                                            if ppp.tag == '{}MAX'.format(xmlns):
                                                item['max'] = ppp.get('value')
                                            if ppp.tag == '{}OPTION'.format(xmlns):
                                                options.append(ppp.get('value'))
                                        item['options'] = ','.join(options)
                                job_def[group][name] = item
                    if group == 'used':
                        for p in elt:
                            order += 1
                            name = p.get('name')
                            keys.append(name)
                            ref = p.get('ref')
                            if ref:
                                item = {
                                    'datatype': job_def.get('parameters').get(ref).get('datatype', 'xs:string'),
                                    'default': job_def.get('parameters').get(ref).get('default'),
                                    'content_type': p.get('xtype'),
                                    'annotation': job_def.get('parameters').get(ref).get('annotation'),
                                    'url': '',
                                }
                            else:
                                item = {
                                    'datatype': 'xs:string',  # may be changed below
                                    'default': p.get('value'),
                                    'content_type': p.get('xtype'),
                                    'annotation': '',  # filled below
                                    'url': '',
                                }
                            for pp in p:
                                if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                    if not ref:
                                        item['annotation'] = pp.text
                                if pp.tag == '{}LINK'.format(xmlns):
                                    purl = pp.get('href')
                                    item['url'] = purl
                                    if 'file://' in purl:
                                        item['datatype'] = 'file'
                            job_def[group][name] = item
                    if group == 'generated':
                        for p in elt:
                            order += 1
                            name = p.get('name')
                            keys.append(name)
                            ref = p.get('ref')
                            if ref:
                                item = {
                                    'default': job_def.get('parameters').get(ref).get('default'),
                                    'content_type': p.get('xtype'),
                                    'annotation': job_def.get('parameters').get(ref).get('annotation'),
                                }
                            else:
                                item = {
                                    'default': p.get('value'),
                                    'content_type': p.get('xtype'),
                                    'annotation': '',  # filled below
                                }
                                for pp in p:
                                    if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                        item['annotation'] = pp.text
                            job_def[group][name] = item
                    job_def[group + '_keys'] = keys
            # Log votable access
            # frame, filename, line_number, function_name, lines, index = inspect.stack()[1]
            # logger.debug('VOTable read at {} ({}:{}): {}'.format(function_name, filename, line_number, fname))
        except IOError:
            # if file does not exist, continue and return an empty dict
            logger.debug('VOTable not found for job {}'.format(jobname))
            raise UserWarning('VOTable not found for job {}'.format(jobname))
        except Exception as e:
            logger.error('{}'.format(e))
            raise
            # return {}
        self.content.update(job_def)


class WADLFile(JDLFile):

    def __init__(self, jdl_path=JDL_PATH, scripts_path=SCRIPTS_PATH):
        self.extension = '.wadl'
        self.jdl_path = os.path.join(jdl_path, 'wadl')
        self.scripts_path = scripts_path
        self.xmlns_uris = {
            'xmlns:wadl': 'http://wadl.dev.java.net/2009/02',
            'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation':
                'http://wadl.dev.java.net/2009/02 '
                'http://www.w3.org/Submission/wadl/wadl.xsd',
        }

    def save(self, jobname):
        """Save job description to WADL file"""
        raw_jobname = jobname
        raw_jobname = raw_jobname.split('/')[-1]  # remove new/ prefix
        # Prepare parameter blocks
        jdl_params = []
        jdl_popts = []
        for pname, p in self.content['parameters'].items():
            # pline = '<param style="query" name="{}" type="{}" required="{}" default="{}"><doc>{}</doc></param>' \
            #        ''.format(pname, p['type'], p['required'], p['default'], p.get('annotation', ''))
            pelt_attrib = {
                'style': 'query',
                'name': pname,
                'type': p['datatype'],
                'required': str(p['required']),
                'default': p['default']
            }
            pelt = ETree.Element('param', attrib=pelt_attrib)
            ETree.SubElement(pelt, 'doc').text = p.get('annotation', '')
            jdl_params.append(pelt)
            # line = '<option value="{}" content_type="text/plain"><doc>{}</doc></option>' \
            #        ''.format(pname, p['annotation'])
            poelt = ETree.Element('option', attrib={
                'value': pname,
                'content_type': 'text/plain'
            })
            ETree.SubElement(poelt, 'doc').text = p.get('annotation', '')
            jdl_popts.append(poelt)
        # Prepare result block
        jdl_ropts = []
        for rname, r in self.content['generated'].items():
            # rline = '<option value="{}" content_type="{}" default="{}"><doc>{}</doc></option>' \
            #         ''.format(rname, r['content_type'], r['default'], r.get('annotation', ''))
            roelt = ETree.Element('option', attrib={
                'value': rname,
                'content_type': r['content_type'],
                'default': r['default']
            })
            ETree.SubElement(roelt, 'doc').text = r.get('annotation', '')
            jdl_ropts.append(roelt)
        # Read WADL UWS template as XML Tree
        filename = '{}/uws_template.wadl'.format(JDL_PATH)
        with open(filename, 'r') as f:
            jdl_string = f.read()
        jdl_tree = ETree.fromstring(jdl_string)
        xmlns = '{' + jdl_tree.nsmap[None] + '}'
        # Insert raw_jobname as the resource path
        joblist_block = jdl_tree.find(".//{}resource[@id='joblist']".format(xmlns))
        joblist_block.set('path', raw_jobname)
        joblist_block.set('doculink', self.content['doculink'])
        joblist_block.set('contact_name', self.content['contact_name'])
        #joblist_block.set('contact_affil', self.content['contact_affil'])
        joblist_block.set('contact_email', self.content['contact_email'])
        # Insert job description
        job_list_description_block = jdl_tree.find(".//{}doc[@title='description']".format(xmlns))
        job_list_description_block.text = self.content['annotation']  # .decode()
        # Insert parameters
        params_block = {}
        for block in ['create_job_parameters', 'control_job_parameters', 'set_job_parameters']:
            params_block[block] = jdl_tree.find(".//{}request[@id='{}']".format(xmlns, block))
            for pelt in jdl_params:
                params_block[block].append(copy.copy(pelt))
        # Insert parameters as options
        param_opts_block = jdl_tree.find(".//{}param[@name='parameter-name']".format(xmlns))
        for poelt in jdl_popts:
            param_opts_block.append(poelt)
        # Insert results as options
        result_opts_block = jdl_tree.find(".//{}param[@name='result-id']".format(xmlns))
        for roelt in jdl_ropts:
            result_opts_block.append(roelt)
        # Insert default execution duration
        execdur_block = jdl_tree.find(".//{}param[@name='EXECUTIONDURATION']".format(xmlns))
        execdur_block.set('default', self.content['executionduration'])
        # Insert default quote
        quote_block = jdl_tree.find(".//{}representation[@id='quote']".format(xmlns))
        quote_block.set('default', self.content['quote'])
        jdl_content = ETree.tostring(jdl_tree, pretty_print=True)
        jdl_fname = self._get_filename(jobname)
        with open(jdl_fname, 'w') as f:
            f.write(jdl_content)
            logger.info('WADL saved: ' + jdl_fname)


    def read(self, jobname):
        """Read job description from WADL file"""
        fname = self._get_filename(jobname)
        # '{}/{}{}'.format(JDL_PATH, job.jobname, self.extension)
        parameters = collections.OrderedDict()
        results = collections.OrderedDict()
        used = collections.OrderedDict()
        try:
            with open(fname, 'r') as f:
                jdl_string = f.read()
            jdl_tree = ETree.fromstring(jdl_string)
            # Get default namespace
            xmlns = '{' + jdl_tree.nsmap[None] + '}'
            # Read parameters description
            params_block = jdl_tree.find(".//{}request[@id='create_job_parameters']".format(xmlns))
            for p in params_block.getchildren():
                pname = p.get('name')
                if pname not in ['PHASE', None]:
                    parameters[pname] = {
                        'datatype': p.get('type'),
                        'required': p.get('required'),
                        'default': p.get('default'),
                        'annotation': list(p)[0].text,
                    }
                    for attr in ['min', 'max', 'choices']:
                        if p.get(attr):
                            parameters[pname][attr] = p.get(attr)
                    if p.get('type') in ['xs:anyURI', 'file']:
                        item = {
                            'default': parameters[pname]['default'],
                            'content_type': '',
                            'annotation': parameters[pname]['annotation']
                        }
                        used[pname] = item
            # Read results description
            results_block = jdl_tree.find(".//{}param[@name='result-id']".format(xmlns))
            for r in results_block.getchildren():
                if r.get('value') not in [None]:
                    ctype = r.get('content_type')
                    if not ctype:
                        ctype = r.get('mediaType')
                    results[r.get('value')] = {
                        'content_type': ctype,
                        'default': r.get('default'),
                        'annotation': list(r)[0].text,
                    }
            job_def = {
                'name': jobname,
                'parameters': parameters,
                'used': used,
                'generated': results,
            }
            # Read job description
            joblist_description_block = jdl_tree.find(".//{}doc[@title='description']".format(xmlns))
            job_def['annotation'] = joblist_description_block.text
            # Read job attributes
            joblist_block = jdl_tree.find(".//{}resource[@id='joblist']".format(xmlns))
            job_def['doculink'] = joblist_block.get('doculink')
            job_def['contact_name'] = joblist_block.get('contact_name')
            #job_def['contact_affil'] = joblist_block.get('contact_affil')
            job_def['contact_email'] = joblist_block.get('contact_email')
            # Read execution duration
            execdur_block = jdl_tree.find(".//{}param[@name='EXECUTIONDURATION']".format(xmlns))
            job_def['executionduration'] = execdur_block.get('default')
            # Read default quote
            quote_block = jdl_tree.find(".//{}representation[@id='quote']".format(xmlns))
            job_def['quote'] = quote_block.get('default')
            # Log wadl access
            frame, filename, line_number, function_name, lines, index = inspect.stack()[1]
            # logger.debug('WADL read at {} ({}:{}): {}'.format(function_name, filename, line_number, fname))
        except IOError:
            # if file does not exist, continue and return an empty dict
            logger.debug('WADL not found for job {}'.format(jobname))
            raise UserWarning('WADL not found for job {}'.format(jobname))
            # return {}
        self.content.update(job_def)


# ----------
# Convert JDL File


def update_vot(jobname):
    logger.info('Updating VOTFile for {}'.format(jobname))
    vot = VOTFile()
    vot.read_old(jobname)
    vot.content['executionDuration'] = vot.content['executionduration']
    vot.save(jobname)
    vot.read(jobname)


def wadl2vot(jobname):
    logger.info('Convert WADLFile to VOTFile for {}'.format(jobname))
    wadl = WADLFile()
    vot = VOTFile()
    wadl.read(jobname)
    vot.content = wadl.content
    vot.save(jobname)
    vot.read(jobname)  # test if file can be read


def vot2json(jobname):
    logger.info('Convert VOTFile to JSONFile for {}'.format(jobname))
    js = JSONFile()
    vot = VOTFile()
    vot.read(jobname)
    js.content = vot.content
    js.save(jobname)
    js.read(jobname)  # test if file can be read


# ---------
# Import PAR files (ftools, ctools)


def read_par(jobname):
    """
    Read .par file that contains the parameter list for a given tool
    The format of the file is from ftools/pfile, also used by ctools,
    it is an ASCII file with the following columns:
    name, type, parameter mode, default value, lower limit, upper limit, prompt
    See: http://heasarc.gsfc.nasa.gov/ftools/others/pfiles.html
    """
    type_dict = {
        'b': 'xs:boolean',
        'i': 'xs:long',
        'r': 'xs:double',
        's': 'xs:string',
        'f': 'xs:string'
    }
    filename = jobname+'.par'
    from astropy.io import ascii
    cnames = ['name', 'type', 'mode', 'default', 'lower', 'upper', 'prompt']
    data = ascii.read(filename, data_start=0, names=cnames)
    job_par = data
    for p in job_par:
        # Set if parameter is required (mode q and a)
        required = 'false'
        if ('q' in p['mode']) or ('a' in p['mode']):
            required = 'true'
        # If param is an integer or a real, add lower and upper limits (if not 0,0)
        lowup = ''
        if (('i' in p['type']) or ('r' in p['type'])) and (p['lower'] != '0' and p['upper'] != 0):
            lowup = ' lower="%s" upper="%s"' % (p['lower'], p['upper'])
        # If param is a string (but not 'mode'), does it have limited choices?
        choices = ''
        if ('s' in p['type']) and (p['lower'] != '') and (p['name'] != 'mode'):
            choices = ' choices="%s"' % (p['lower'])
        # Write param block to file
