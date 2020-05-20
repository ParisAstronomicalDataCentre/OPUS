#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Export UWS job description to a ProvDocument following the W3C PROV standard
"""

import os
import copy
import prov
from prov.model import ProvDocument, ProvBundle
from prov.dot import prov_to_dot
from pydotplus.graphviz import InvocationException

from .settings import *
from . import uws_classes
from . import storage
from . import uws_jdl

# examples:
# http://prov.readthedocs.org/en/latest/usage.html#simple-prov-document
# http://lists.g-vo.org/pipermail/prov-adhoc/2015-June/000025.html


def job2prov(jobid, user, depth=1, direction='BACK', members=0, steps=0, agent=1, model='IVOA',
             descriptions=0, configuration=1, attributes=1,
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
    if configuration:
        show_parameters = True
    else:
        show_parameters = False

    # Load job
    job = uws_classes.Job('', jobid, user, get_attributes=True, get_parameters=True, get_results=True)

    # Load JDL
    job.jdl.read(job.jobname, jobid=job.jobid)

    # Declaring namespaces for various prefixes used in the example
    pdoc.set_default_namespace('http://uws-server.readthedocs.io#')  # point to OPUS doc
    pdoc.add_namespace('prov', 'http://www.w3.org/ns/prov#')
    pdoc.add_namespace('foaf', 'http://xmlns.com/foaf/0.1/')
    pdoc.add_namespace('voprov', 'http://www.ivoa.net/documents/ProvenanceDM#')
    pdoc.add_namespace('uws', 'http://www.ivoa.net/xml/UWS/v1.1#')
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
    act_id = 'opus_job:' + job.jobname + '/' + job.jobid
    act = pdoc.activity(act_id, job.start_time, job.end_time)
    act.add_attributes({
        'prov:label': job.jobname,  # + '/' + job.jobid,
    })
    #for attr in ['doculink', 'type', 'subtype', 'version']:
    #    value = job.jdl.content.get(attr, None)
    #    if value:
    #        act.add_attributes({
    #            'voprov:' + attr: value,
    #        })

    # Agent: owner of the job
    if agent:
        owner = pdoc.agent('opus_user:' + job.owner)
        owner.add_attributes({
            'prov:label': job.owner,
            #'foaf:name': job.owner,
        })
        act.wasAssociatedWith(owner, attributes={
            'prov:role': 'owner'
        })

    # ActivityDescription
    if depth != 0 and descriptions:
        adesc = pdoc.entity('opus_jdl:' + job.jobname)
        adesc.add_attributes({
            'prov:label': job.jobname + " description",
            'prov:type': 'voprov:ActivityDescription',
        })
        adesc.add_attributes({
            'prov:type': 'prov:Plan',
            'prov:type': 'prov:Collection'
        })
        pdoc.influence(act, adesc)  #, other_attributes={
        #    'prov:type': 'voprov:Description',
        #})
        adattrs = {}
        for pkey in ['name', 'annotation', 'version', 'type', 'subtype', 'doculink']:
            pvalue = job.jdl.content.get(pkey)
            if pvalue:
                if pkey == 'annotation':
                    adattrs['voprov:description'] = pvalue
                else:
                    adattrs['voprov:' + pkey] = pvalue
        for pkey in ['executionDuration', 'quote']:
            pvalue = job.jdl.content.get(pkey)
            if pvalue:
                adattrs['uws:' + pkey] = pvalue
        adesc.add_attributes(adattrs)

    # Agent: contact for the job in ActivityDescription
    if agent:
        contact_name = job.jdl.content.get('contact_name')
        contact_email = job.jdl.content.get('contact_email')
        if contact_email and not contact_name:
            contact_name = contact_email
        if contact_name:
            # Is contact name in the server user list?
            contact_id = contact_name
            users_dicts = job.storage.get_users()
            users = [u['name'] for u in users_dicts]
            if contact_id in users:
                contact_id = 'opus_user:' + contact_id
            contact = pdoc.agent(contact_id)
            contact.add_attributes({
                'prov:label': contact_name,
                #'foaf:name': contact_name,
            })
            if contact_email:
                contact.add_attributes({
                    'foaf:mbox': "<mailto:{}>".format(contact_email)
                })
            if descriptions:
                adesc.wasAttributedTo(contact, attributes={
                    'prov:role': 'contact'
                })

    # Used entities
    e_in = []
    act_attr = {}
    used_entities = []
    eds = []

    for pname, pdict in job.jdl.content.get('used', {}).items():

        value = job.parameters.get(pname, {}).get('value', '')
        label = pname
        entity_id = job.parameters.get(pname, {}).get('entity_id', None)
        logger.debug('Search for entity {} (pname={}, value={})'.format(entity_id, pname, value))
        entity = job.storage.get_entity(entity_id, silent=True)
        if entity:
            # Entity recorded in DB
            used_entities.append(entity_id)
            pqns = [ns_result + ':' + entity_id]
            label = entity['file_name']
            location = entity['access_url']
            logger.debug('Input entity found: {}'.format(entity))
        elif '//' in value:
            # Entity is a file or a URL (not a value or an ID)
            pqns = [value.split('//')[-1]]  # removes file:// if present, or longer path
            used_entities.append(pqns[0])
            location = value
            logger.debug('No record found for input entity {}={}, assuming it is a file or a URL'.format(pname, value))
        else:
            # Entity is a value or an ID
            location = None
            if '*' in pdict['multiplicity'] or int(pdict['multiplicity']) > 1:
                sep = pdict.get('separator', ' ')
                if ',' in value:
                    sep = ','
                pqns = value.split(sep)
            else:
                pqns = [value]

        # Explore used entities for the activity if depth > 0
        if depth != 0:

            # Add EntityDescription
            edattrs = {}
            for pkey, pvalue in pdict.items():
                if pvalue and pkey not in ['default']:
                    edattrs['voprov:' + pkey] = pvalue
            if descriptions > 1:
                edattrs['prov:label'] = pname
                edattrs['prov:type'] = 'voprov:EntityDescription'
                eds.append(pdoc.entity('opus_jdl:' + job.jobname + '#' + pname))
                eds[-1].add_attributes(edattrs)
                adesc.hadMember(eds[-1])

            for pqn in pqns:

                # Add Entity
                e_in.append(pdoc.entity(pqn))
                e_in[-1].add_attributes({
                    'prov:label': label,
                    # 'prov:value': value,
                    'prov:location': location,
                    # 'prov:type': pdict['datatype'],
                })

                # Add Used relation
                act.used(e_in[-1], attributes={
                    'prov:role': pname
                })

                if not descriptions:
                    # Add attributes to the entity directly
                    for attrkey in ['voprov:content_type', 'voprov:file_name', 'voprov:result_name']:
                        if attrkey in edattrs:
                            e_in[-1].add_attributes({attrkey: edattrs[attrkey]})
                elif descriptions > 1:
                    pdoc.influence(e_in[-1], eds[-1], other_attributes={
                        'prov:type': 'voprov:EntityDescription',
                    })

                if entity:
                    # Add more attributes to the entity
                    e_in[-1].add_attributes({
                        'voprov:content_type': entity['content_type'],
                        'voprov:result_name': entity['result_name'],
                        'voprov:file_name': entity['file_name'],
                    })

                    # Explores entity origin if depth > 1
                    if depth != 1 and entity['jobid']:
                        # other_job = copy.deepcopy(job)
                        # other_job = uws_classes.Job('', entity['jobid'], job.user, get_attributes=True,
                        #                             get_parameters=True, get_results=True)
                        # job.storage.read(other_job, get_attributes=True, get_parameters=True, get_results=True)
                        other_pdocs.append(
                            job2prov(
                                entity['jobid'], job.user,
                                depth=depth-2, direction=direction, members=members, steps=steps, agent=agent, model=model,
                                descriptions=descriptions, configuration=configuration,
                                show_parameters=show_parameters,
                                recursive=True
                            )
                        )

    # Parameters that influence the activity (if depth > 0)
    params = []
    pds = []

    if depth != 0 and show_parameters:

        # Add Parameter Collection?
        # all_params = pdoc.collection('opus_job:' + job.jobname + '/' + job.jobid + '/parameters')

        for pname, pdict in job.jdl.content.get('parameters', {}).items():

            # Add Parameter
            pqn = ns_jdl + ':' + pname
            if pname in job.parameters:
                value = job.parameters[pname]['value']
            else:
                value = pdict['default']
            params.append(pdoc.entity('opus_job:' + job.jobname + '/' + job.jobid + '/parameters/' + pname))
            pattrs = {
                'prov:label': pname,
                'prov:type': 'voprov:Parameter',
                'prov:value': value,
            }
            params[-1].add_attributes(pattrs)

            # Activity-Parameter relation
            pdoc.influence(act, params[-1])  #, other_attributes={
            #     'prov:type': 'voprov:wasConfiguredBy',
            #})

            # Add ParameterDescription
            pdattrs = {}
            for pkey, pvalue in pdict.items():
                if pvalue:
                    pdattrs['voprov:' + pkey] = pvalue
            if descriptions > 1:
                pdattrs['prov:label'] = pname + "description"
                pdattrs['prov:type'] = 'voprov:ParameterDescription'
                pds.append(pdoc.entity('opus_jdl:' + job.jobname + '#' + pname))
                pds[-1].add_attributes(pdattrs)
                pdoc.influence(params[-1], pds[-1], other_attributes={
                    'prov:type': 'voprov:ParameterDescription',
                })
                adesc.hadMember(pds[-1])
            else:
                # Add attributes to the parameter directly
                params[-1].add_attributes(pdattrs)

            # Member of Collection
            # all_params.hadMember(params[-1])

        # Activity-Collection relation
        # pdoc.influence(act, all_params)

    # Generated entities (if depth > 0)
    if depth != 0 or recursive or show_generated:
        # Check if internal provenance is given, add as a generated bundle? or directly?
        inpfile = os.path.join(JOBDATA_PATH, jobid, "internal_provenance.json")
        if os.path.isfile(inpfile):
            inpdoc = prov.read(inpfile)
            inpbundle = ProvBundle(namespaces=inpdoc.namespaces, identifier="bundle_" + job.jobid + "_prov")
            #inpbundle._identifier = "id:" + job.jobid + "_prov"
            inpbundle.update(inpdoc)
            #inpprov = inpdoc.bundle(job.jobid + "_prov")
            pdoc.add_bundle(inpbundle)
            pdoc.wasGeneratedBy(inpbundle.identifier, act)
            #pdoc.update(inpdoc)
            #for rec in inpdoc.get_records():
            #    if "Activity" in str(rec.get_type()):
            #        inf_act = pdoc.get_record(rec.identifier)[0]
            #        inf_act.wasInformedBy(act)
        e_out = []
        for rname in job.results:
            if rname not in ['stdout', 'stderr', 'provjson', 'provxml', 'provsvg']:
                entity_id = job.results[rname]['entity_id']
                # entity_id = job.jobid + '_' + rname
                # if entity_id:
                entity = job.storage.get_entity(entity_id, silent=True)
                if entity:
                    entity_id = entity['entity_id']
                    rqn = ns_result + ':' + entity_id
                    content_type = entity['content_type']
                else:
                    entity_id = rname
                    rqn = ':' + entity_id
                    content_type = job.results[rname]['content_type']

                # Only show result if it is not already used (case of config files sometimes)
                if entity_id not in used_entities:

                    # Add Entity
                    e_out.append(pdoc.entity(rqn))
                    eattrs = {
                        'prov:location': job.results[rname]['url'],
                        'voprov:content_type': content_type,
                    }
                    if entity:
                        eattrs['prov:label'] = entity['file_name']
                        eattrs['voprov:result_name'] = entity['result_name']
                        eattrs['voprov:file_name'] = entity['file_name']
                        pdict = job.jdl.content['generated'].get(entity['result_name'], {})
                    if not 'prov:label' in eattrs:
                        eattrs['prov:label'] = rname
                    e_out[-1].add_attributes(eattrs)

                    # Add Generation relation
                    e_out[-1].wasGeneratedBy(act, attributes={
                        'prov:role': rname,
                    })
                    #for e in e_in:
                    #    e_out[-1].wasDerivedFrom(e)
                    #if agent:
                    #    e_out[-1].wasAttributedTo(owner, attributes={
                    #        'prov:role': 'owner',
                    #    })
                    if entity.get("from_entity", None):
                        e_from = inpbundle.get_record(entity["from_entity"])[0]
                        e_out[-1].wasDerivedFrom(e_from)
                        #copy_act = pdoc.activity(act_id + '_copy_to_datastore', other_attributes={"prov:label": "copy_to_datastore"})
                        #copy_act.wasInformedBy(act)
                        #copy_act.used(entity["from_entity"])
                        #e_out[-1].wasGeneratedBy(copy_act)

                    if pdict:
                        # Add EntityDescription
                        edattrs = {}
                        for pkey, pvalue in pdict.items():
                            if pvalue:
                                edattrs['voprov:' + pkey] = pvalue
                        if descriptions > 1:
                            edattrs['prov:label'] = entity['result_name']
                            edattrs['prov:type'] = 'voprov:EntityDescription'
                            eds.append(pdoc.entity('opus_jdl:' + job.jobname + '#' + entity['result_name']))
                            eds[-1].add_attributes(edattrs)
                            pdoc.influence(e_out[-1], eds[-1], other_attributes={
                                'prov:type': 'voprov:EntityDescription',
                            })
                            adesc.hadMember(eds[-1])
                        #else:
                        #    e_out[-1].add_attributes(edattrs)

    # Merge all prov documents
    for opdoc in other_pdocs:
        #logger.debug(opdoc.serialize())
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


def prov2dot(prov_doc, attributes=True, direction='BT'):
    """
    Convert ProvDocument to dot graphical format
    :param prov_doc:
    :return:
    """
    dot = prov_to_dot(prov_doc, use_labels=True, show_element_attributes=attributes, show_relation_attributes=attributes, direction=direction)
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


def prov2svg_content(prov_doc, attributes=True, direction='BT'):
    """
    Convert ProvDocument to dot graphical format
    :param prov_doc:
    :param fname: file name
    :return:
    """
    try:
        dot = prov2dot(prov_doc, attributes=attributes, direction=direction)
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
