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
from . import storage

# examples:
# http://prov.readthedocs.org/en/latest/usage.html#simple-prov-document
# http://lists.g-vo.org/pipermail/prov-adhoc/2015-June/000025.html


def job2prov(job, depth=1, direction='BACK', members=0, steps=0, agent=0, model='IVOA',
             show_parameters=True, recursive=False, show_generated=False):
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

    # Init
    pdoc = ProvDocument()
    other_pdocs = []
    # Get new storage instance
    job_storage = getattr(storage, STORAGE + 'JobStorage')()
    # Update JDL content
    job.jdl.read(job.jobname, jobid=job.jobid)

    # Declaring namespaces for various prefixes used in the example
    pdoc.set_default_namespace('http://uws-server.readthedocs.io#')  # point to OPUS doc
    pdoc.add_namespace('prov', 'http://www.w3.org/ns/prov#')
    pdoc.add_namespace('foaf', 'http://xmlns.com/foaf/0.1/')
    pdoc.add_namespace('voprov', 'http://www.ivoa.net/documents/ProvenanceDM#')
    pdoc.add_namespace('opus_user', BASE_URL + '/user/')
    ns_result = 'opus_store'
    pdoc.add_namespace('opus_store', BASE_URL + '/store/?ID=')
    pdoc.add_namespace('opus_job', BASE_URL + '/rest/')
    pdoc.add_namespace('opus_jdl', BASE_URL + '/jdl/')
    ns_jdl = job.jobname
    pdoc.add_namespace(ns_jdl, BASE_URL + '/jdl/' + job.jobname + '/votable#')
    # ns_job = job.jobname + '/' + job.jobid
    # pdoc.add_namespace(ns_job, BASE_URL + '/jdl/' + job.jobname + '/votable#')

    # Activity
    act = pdoc.activity('opus_job:' + job.jobname + '/' + job.jobid, job.start_time, job.end_time)
    for attr in ['doculink', 'type', 'subtype', 'version']:
        value = job.jdl.content.get(attr, None)
        if value:
            act.add_attributes({
                'voprov:' + attr: value,
            })

    # Agent: owner of the job
    if agent:
        owner = pdoc.agent('opus_user:' + job.owner)
        # owner.add_attributes({
        #     'foaf:name': job.owner,
        # })
        act.wasAssociatedWith(owner, attributes={
            'prov:role': 'owner'
        })

    # Plan = ActivityDescription
    if depth > 0:
        plan = pdoc.entity('opus_jdl:' + job.jobname)
        plan.add_attributes({
            'prov:type': 'voprov:ActivityDescription'
        })
        pdoc.influence(act, plan, other_attributes={
            # 'prov:type': 'voprov:ActivityDescription',
        })

    # Agent: contact for the job in ActivityDescription
    if agent:
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
        # Assuming that used entity is a file or a URL (not a value or an ID)
        value = job.parameters.get(pname, {}).get('value', '')
        entity_id = job.parameters.get(pname, {}).get('entity_id', None)
        logger.debug('Search for entity: {}'.format(entity_id))
        # entity_id = os.path.splitext(os.path.basename(value))[0]
        entity = job_storage.get_entity(entity_id, silent=True)
        if entity:
            pqn = ns_result + ':' + entity_id
            location = entity['access_url']
            logger.debug('Input entity found: {}'.format(entity))
        else:
            pqn = ':' + value.split('/')[-1]
            location = value
            logger.debug('No previous record for input entity {}={}'.format(pname, value))
        if show_parameters:
            if value:
                act_attr[ns_jdl + ':' + pname] = value

        # Explore used entities for the activity if depth > 0
        if depth != 0:
            e_in.append(pdoc.entity(pqn))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            e_in[-1].add_attributes({
                # 'prov:value': value,
                'prov:location': location,
                # 'prov:type': pdict['datatype'],
            })
            act.used(e_in[-1], attributes={
                'prov:role': pname
            })
            if entity:
                e_in[-1].add_attributes({
                    'voprov:result_name': entity['result_name'],
                    'voprov:file_name': entity['file_name'],
                    'voprov:content_type': entity['content_type'],
                })

                # Explores entity origin if depth > 1
                if depth != 1 and entity['jobid']:
                    other_job = copy.copy(job)
                    other_job.jobid = entity['jobid']
                    job_storage.read(other_job, get_attributes=True, get_parameters=True, get_results=True)
                    other_pdocs.append(job2prov(other_job, depth=depth-2, recursive=True))

    # Parameters that influence the activity (if depth > 0)
    params = []
    if depth != 0 and show_parameters:
        # all_params = pdoc.collection('opus_job:' + job.jobname + '/' + job.jobid + '/parameters')
        for pname, pdict in job.jdl.content.get('parameters', {}).items():
            pqn = ns_jdl + ':' + pname
            if pname in job.parameters:
                value = job.parameters[pname]['value']
            else:
                value = pdict['default']
            # act_attr[pqn] = value
            params.append(pdoc.entity('opus_job:' + job.jobname + '/' + job.jobid + '/parameters/' + pname))
            pattrs = {
                'prov:type': 'voprov:Parameter',
                'prov:value': value,
            }
            for pkey, pvalue in pdict.items():
                if pvalue:
                    pattrs['voprov:' + pkey] = pvalue
            params[-1].add_attributes(pattrs)
            pdoc.influence(act, params[-1], other_attributes={
                 # 'prov:type': 'voprov:hadConfiguration',
            })
            # all_params.hadMember(params[-1])
        # pdoc.influence(act, all_params)
        # if len(act_attr) > 0:
        #     act.add_attributes(act_attr)

    # Generated entities (if depth > 0)
    if depth != 0 or recursive or show_generated:
        e_out = []
        for rname in job.results:
            if rname not in ['stdout', 'stderr', 'provjson', 'provxml', 'provsvg']:
                entity_id = job.results[rname]['entity_id']
                # rdict = job.jdl.content['generated'].get(rname, {})
                # entity_id = job.jobid + '_' + rname
                # if entity_id:
                entity = job_storage.get_entity(entity_id, silent=True)
                if entity:
                    entity_id = entity['entity_id']
                    rqn = ns_result + ':' + entity_id
                    content_type = entity['content_type']
                else:
                    entity_id = rname
                    rqn = ':' + entity_id
                    content_type = job.results[rname]['content_type']
                e_out.append(pdoc.entity(rqn))
                # TODO: use publisher_did? add prov attributes, add voprov attributes?
                e_out[-1].add_attributes({
                    'prov:location': job.results[rname]['url'],
                    # 'voprov:result_name': entity['result_name'],
                    # 'voprov:file_name': entity['file_name'],
                    'voprov:content_type': content_type,
                })
                # test if not used
                used = job_storage.session.query(job_storage.Used).filter_by(entity_id=entity_id, jobid=job.jobid).all()
                if not used:
                    e_out[-1].wasGeneratedBy(act, attributes={
                        'prov:role': rname,
                    })
                    #for e in e_in:
                    #    e_out[-1].wasDerivedFrom(e)
                    if agent:
                        e_out[-1].wasAttributedTo(owner, attributes={
                            'prov:role': 'owner',
                        })

    # Merge all prov documents
    for opdoc in other_pdocs:
        logger.debug(opdoc.serialize())
        pdoc.update(opdoc)
    pdoc.flattened()
    pdoc.unified()

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
