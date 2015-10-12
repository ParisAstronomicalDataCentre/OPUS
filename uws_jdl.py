# -*- coding: utf-8 -*-
"""
Created on Oct 9 11:30:00 2015

@author: mservillat
"""

import collections
import inspect
import copy
import lxml.etree as ETree
from settings import *


# ---------
# WADL as Job Description Language

# xmlns = '{http://wadl.dev.java.net/2009/02}'
xmlns_uris = {'xmlns:wadl': 'http://wadl.dev.java.net/2009/02',
              'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
              'xmlns:xlink': 'http://www.w3.org/1999/xlink',
              'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
              'xsi:schemaLocation': 'http://wadl.dev.java.net/2009/02 http://www.w3.org/Submission/wadl/wadl.xsd'}

def read_wadl(jobname):
    """Read job description from WADL file"""
    fname = '{}/{}.wadl'.format(WADL_PATH, jobname)
    parameters = collections.OrderedDict()
    results = collections.OrderedDict()
    try:
        with open(fname, 'r') as f:
            wadl_string = f.read()
        wadl_tree = ETree.fromstring(wadl_string)
        xmlns = '{' + wadl_tree.nsmap[None] + '}'
        # Read parameters description
        params_block = wadl_tree.find(".//{}request[@id='create_job_parameters']".format(xmlns))
        for p in params_block.getchildren():
            if p.get('name') not in ['PHASE', None]:
                parameters[p.get('name')] = {
                    'type': p.get('type'),
                    'required': p.get('required'),
                    'default': p.get('default'),
                    'description': list(p)[0].text,
                }
        # Read results description
        results_block = wadl_tree.find(".//{}param[@name='result-id']".format(xmlns))
        for r in results_block.getchildren():
            if r.get('value') not in [None]:
                results[r.get('value')] = {
                    'mediaType': r.get('mediaType'),
                    'default': r.get('default'),
                    'description': list(r)[0].text,
                }
        # Read default execution duration
        execdur_block = wadl_tree.find(".//{}param[@name='EXECUTIONDURATION']".format(xmlns))
        execdur = execdur_block.get('default')
        # Read job description
        job_list_description_block = wadl_tree.find(".//{}doc[@title='description']".format(xmlns))
        description = job_list_description_block.text
        # Log wadl access
        frame, filename, line_number, function_name, lines, index = inspect.stack()[1]
        logger.debug('WADL read at {} ({}:{}): {}'.format(function_name, filename, line_number, fname))
    except IOError:
        # if file does not exist, continue and return an empty dict
        logger.debug('WADL not found for job {}'.format(jobname))
        return {}
    job_def = {'description': description,
               'parameters': parameters,
               'results': results,
               'executionduration': execdur,
               'quote': execdur}
    return job_def


def create_wadl(jobname, job_def):
    jobname = jobname.split('/')[-1]
    # Prepare parameter blocks
    wadl_params = []
    wadl_popts = []
    for pname, p in job_def['parameters'].iteritems():
        # pline = '<param style="query" name="{}" type="{}" required="{}" default="{}"><doc>{}</doc></param>' \
        #        ''.format(pname, p['type'], p['required'], p['default'], p.get('description', ''))
        pelt_attrib = {'style': 'query',
                       'name': pname,
                       'type': p['type'],
                       'required': str(p['required']),
                       'default': p['default']}
        pelt = ETree.Element('param', attrib=pelt_attrib)
        ETree.SubElement(pelt, 'doc').text = p.get('description', '')
        wadl_params.append(pelt)
        # line = '<option value="{}" mediaType="text/plain"><doc>{}</doc></option>' \
        #        ''.format(pname, p['description'])
        poelt = ETree.Element('option', attrib={'value': pname, 'mediaType': 'text/plain'})
        ETree.SubElement(poelt, 'doc').text = p.get('description', '')
        wadl_popts.append(poelt)
    # Prepare result block
    wadl_ropts = []
    for rname, r in job_def['results'].iteritems():
        # rline = '<option value="{}" mediaType="{}" default="{}"><doc>{}</doc></option>' \
        #         ''.format(rname, r['mediaType'], r['default'], r.get('description', ''))
        roelt = ETree.Element('option', attrib={'value': rname, 'mediaType': r['mediaType'], 'default': r['default']})
        ETree.SubElement(roelt, 'doc').text = r.get('description', '')
        wadl_ropts.append(roelt)
    # Read WADL UWS template as XML Tree
    filename = '{}/uws_template.wadl'.format(WADL_PATH)
    with open(filename, 'r') as f:
        wadl_string = f.read()
    wadl_tree = ETree.fromstring(wadl_string)
    xmlns = '{' + wadl_tree.nsmap[None] + '}'
    #wadl_tree.
    # Insert blocks
    joblist_block = wadl_tree.find(".//{}resource[@id='joblist']".format(xmlns))
    joblist_block.set('path', jobname)
    params_block = {}
    for block in ['create_job_parameters', 'control_job_parameters', 'set_job_parameters']:
        params_block[block] = wadl_tree.find(".//{}request[@id='{}']".format(xmlns, block))
        for pelt in wadl_params:
            params_block[block].append(copy.copy(pelt))
    param_opts_block = wadl_tree.find(".//{}param[@name='parameter-name']".format(xmlns))
    for poelt in wadl_popts:
        param_opts_block.append(poelt)
    result_opts_block = wadl_tree.find(".//{}param[@name='result-id']".format(xmlns))
    for roelt in wadl_ropts:
        result_opts_block.append(roelt)
    execdur_block = wadl_tree.find(".//{}param[@name='EXECUTIONDURATION']".format(xmlns))
    execdur_block.set('default', job_def['executionduration'])
    job_list_description_block = wadl_tree.find(".//{}doc[@title='description']".format(xmlns))
    job_list_description_block.text = job_def['description']
    # Write WADL file for jobname
    # wadl_fname = '{}/new/{}.wadl'.format(WADL_PATH, jobname)
    # wadl_tree.write(wadl_fname, pretty_print=True)
    return ETree.tostring(wadl_tree, pretty_print=True)

def write_wadl_file(jobname):
    import fileinput
    # copy uws_template.wadl to final file

    # insert parameters and results description
    for line in fileinput.input('uws_template.wadl', inplace=1):
        print line,
        if line.startswith('<!-- INSERT BASE VALUE -->'):
            print 'foo bar'


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
    job_par = np.array(data)
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
