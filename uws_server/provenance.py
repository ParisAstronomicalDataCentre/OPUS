#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Export UWS job description to a ProvDocument following the W3C PROV standard
"""

import os
import copy
from prov.model import ProvDocument
from prov.dot import prov_to_dot
from pydotplus.graphviz import InvocationException

from .settings import *
#from . import storage

# examples:
# http://prov.readthedocs.org/en/latest/usage.html#simple-prov-document
# http://lists.g-vo.org/pipermail/prov-adhoc/2015-June/000025.html


def job2prov(job, show_parameters=True):
    """
    Create ProvDocument based on job description
    :param job: UWS job
    :return: ProvDocument
    """

    # job.jdl.content = {
    #     'description': description,
    #     'parameters': parameters,
    #     'results': results,
    #     'executionduration': execdur,
    #     'quote': quote
    # }
    # parameters[pname] = {
    #     'type': p.get('type'),
    #     'required': p.get('required'),
    #     'default': p.get('default'),
    #     'description': list(p)[0].text,
    # }
    # results[rname] = {
    #     'content_type': r.get('content_type'),
    #     'default': r.get('default'),
    #     'description': list(r)[0].text,
    # }

    pdoc = ProvDocument()
    other_pdocs = []

    # Declaring namespaces for various prefixes used in the example
    pdoc.set_default_namespace('http://uws-server.readthedocs.io#')  # point to OPUS doc
    pdoc.add_namespace('prov', 'http://www.w3.org/ns/prov#')
    pdoc.add_namespace('foaf', 'http://xmlns.com/foaf/0.1/')
    pdoc.add_namespace('voprov', 'http://www.ivoa.net/documents/dm/provdm/voprov#')
    ns_jdl = job.jobname
    pdoc.add_namespace(ns_jdl, BASE_URL + '/jdl/' + job.jobname + '/votable#')
    ns_job = job.jobname + '/' + job.jobid
    pdoc.add_namespace(ns_job, BASE_URL + '/jdl/' + job.jobname + '/votable#')
    ns_result = 'opus_store'
    pdoc.add_namespace('opus_store', BASE_URL + '/get/result/?ID=')
    pdoc.add_namespace('opus_user', BASE_URL + '/user/')

    # Activity
    act = pdoc.activity(ns_jdl + ':' + job.jobid, job.start_time, job.end_time)
    # TODO: add job description, version, url, ...
    act.add_attributes({
        'prov:label': job.jobname,
        'voprov:doculink': job.jdl.content.get('url'),
    })

    # Agent: owner of the job
    owner = pdoc.agent('opus_user:' + job.owner)
    # owner.add_attributes({
    #     'foaf:name': job.owner,
    # })
    act.wasAssociatedWith(owner, attributes={
        'prov:role': 'owner'
    })

    # Agent: contact for the job
    contact_name = job.jdl.content.get('contact_name')
    contact_email = job.jdl.content.get('contact_email')
    if not contact_name:
        contact_name = contact_email
    if contact_name:
        contact = pdoc.agent(contact_name)
        # contact.add_attributes({
        #     'foaf:name': contact_name,
        # })
        if contact_email:
            contact.add_attributes({
                'foaf:mbox': "<mailto:{}>".format(contact_email)
            })
        act.wasAssociatedWith(contact, attributes={
            'prov:role': 'contact'
        })

    # Used entities
    e_in = []
    act_attr = {}
    for pname, pdict in job.jdl.content.get('used', {}).items():
        value = job.parameters.get(pname, {}).get('value', '')
        entity_id = os.path.splitext(os.path.basename(value))[0]
        entity = {}
        try:
            pqn = ns_result + ':' + entity_id
            entity = job.storage.get_entity(entity_id)
            logger.debug('Input entity found: {}'.format(entity))
        except:
            entity_id = job.jobid + '_' + pname
            pqn = ns_result + ':' + entity_id
            logger.debug('No previous record for input entity {}'.format(entity_id))
        e_in.append(pdoc.entity(pqn))
        # TODO: use publisher_did? add prov attributes, add voprov attributes?
        e_in[-1].add_attributes({
            # 'prov:value': value,
            'prov:location': value,
            # 'prov:type': pdict['datatype'],
        })
        if show_parameters:
            act_attr[ns_job + ':' + pname] = value
        act.used(e_in[-1])
        if entity:
            e_in[-1].add_attributes({
                'voprov:result_name': entity['result_name'],
                'voprov:file_name': entity['file_name'],
                'voprov:content_type': entity['content_type'],
            })
            other_job = copy.copy(job)
            other_job.jobid = entity['jobid']
            other_job.storage = job.storage  # getattr(storage, STORAGE + 'JobStorage')()
            other_job.storage.read(other_job, get_attributes=True, get_parameters=True, get_results=True)
            other_pdocs.append(job2prov(other_job))

    # Parameters as Activity attributes
    if show_parameters:
        for pname, pdict in job.jdl.content.get('parameters', {}).items():
            pqn = ns_jdl + ':' + pname
            if pname in job.parameters:
                act_attr[pqn] = job.parameters[pname]['value']
            else:
                act_attr[pqn] = pdict['default']
        if len(act_attr) > 0:
            act.add_attributes(act_attr)

    # Generated entities
    e_out = []
    for rname in job.results:
        if rname not in ['stdout', 'stderr', 'provjson', 'provxml', 'provsvg']:
            rdict = job.jdl.content['generated'][rname]
            entity_id = job.jobid + '_' + rname
            entity = job.storage.get_entity(entity_id)
            rqn = ns_result + ':' + entity_id
            e_out.append(pdoc.entity(rqn))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            e_out[-1].add_attributes({
                'prov:location': job.results[rname]['url'],
                'voprov:result_name': entity['result_name'],
                'voprov:file_name': entity['file_name'],
                'voprov:content_type': entity['content_type'],
            })
            e_out[-1].wasGeneratedBy(act, entity['creation_time'])
            #for e in e_in:
            #    e_out[-1].wasDerivedFrom(e)

    for opdoc in other_pdocs:
        logger.debug(opdoc.serialize())
        pdoc.update(opdoc)

    return pdoc


def prov2json(prov_doc, fname):
    """
    Write ProvDocument as an JSON file
    :param prov_doc: ProvDocument
    :param fname: file name
    :return:
    """
    prov_doc.serialize(fname, format='json')


def prov2xml(prov_doc, fname):
    """
    Write ProvDocument as an XML file
    :param prov_doc: ProvDocument
    :param fname: file name
    :return:
    """
    prov_doc.serialize(fname, format='xml')


def prov2dot(prov_doc):
    """
    Convert ProvDocument to dot graphical format
    :param prov_doc:
    :return:
    """
    dot = prov_to_dot(prov_doc, use_labels=False, show_element_attributes=True, show_relation_attributes=True)
    return dot


def prov2svg(prov_doc, fname):
    """
    Convert ProvDocument to dot graphical format
    :param prov_doc:
    :param fname: file name
    :return:
    """
    try:
        dot = prov2dot(prov_doc)
        svg_content = dot.create(format="svg")
    except InvocationException as e:
        svg_content = '''
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.0"
	width="38" height="32"  viewBox="0 0 39.875 33.6667">
<path style="stroke: none; fill: #323296;" d="M 10,0 L 30.5,0 39.875,17.5 30.5,33.6667 10,33.6667 L 0,17.5 L 10,0 z"/>
</svg>
'''
    with open(fname, "wb") as f:
        f.write(svg_content)


def prov2svg_content(prov_doc):
    """
    Convert ProvDocument to dot graphical format
    :param prov_doc:
    :param fname: file name
    :return:
    """
    try:
        dot = prov2dot(prov_doc)
        svg_content = dot.create(format="svg")
    except InvocationException as e:
        svg_content = '''
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.0"
	width="38" height="32"  viewBox="0 0 39.875 33.6667">
<path style="stroke: none; fill: #323296;" d="M 10,0 L 30.5,0 39.875,17.5 30.5,33.6667 10,33.6667 L 0,17.5 L 10,0 z"/>
</svg>
'''
    return svg_content
