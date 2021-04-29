#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Export UWS job description to a ProvDocument following the W3C PROV standard
"""

import prov
from .voprov_local.models.model import VOProvDocument, VOProvBundle, VOPROV, PROV
# from prov.model import ProvDocument, ProvBundle
from .voprov_local.visualization.dot import prov_to_dot
from pydotplus.graphviz import InvocationException

from .settings import *
from . import uws_classes

# examples:
# http://prov.readthedocs.org/en/latest/usage.html#simple-prov-document
# http://lists.g-vo.org/pipermail/prov-adhoc/2015-June/000025.html

INTERNAL_PROVENANCE_FILENAME = "internal_provenance.json"


def job2prov(jobid, user, depth=1, direction='BACK', members=0, agents=1, model='IVOA',
             descriptions=0, configuration=1, attributes=1,
             show_used=False, show_generated=False):
    """
    Create ProvDocument based on job description
    :param jobid: UWS job
    :param user: current user
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
    pdoc = VOProvDocument()
    other_pdocs = []
    w3c = False
    if model == 'W3C':
        w3c = True

    # Load job
    job = uws_classes.Job('', jobid, user, get_attributes=True, get_parameters=True, get_results=True)

    # Load JDL
    job.jdl.read(job.jobname, jobid=job.jobid)

    # Declaring namespaces for various prefixes used in the example
    pdoc.set_default_namespace(VOPROV.uri)
    pdoc.add_namespace('voprov', VOPROV.uri)
    pdoc.add_namespace('prov', PROV.uri)
    pdoc.add_namespace('foaf', 'http://xmlns.com/foaf/0.1/')
    pdoc.add_namespace('uws', 'http://www.ivoa.net/xml/UWS/v1.1#')
    pdoc.add_namespace('opus_user', BASE_URL + '/user/')
    ns_result = 'opus_store'
    pdoc.add_namespace(ns_result, BASE_URL + '/store/?ID=')
    pdoc.add_namespace('opus_job', BASE_URL + '/rest/')
    pdoc.add_namespace('opus_jdl', BASE_URL + '/jdl/')
    pdoc.add_namespace('media-type', 'https://www.w3.org/ns/iana/media-types/')
    ns_jdl = job.jobname
    pdoc.add_namespace(ns_jdl, BASE_URL + '/jdl/' + job.jobname + '/votable#')
    # ns_job = job.jobname + '/' + job.jobid
    # pdoc.add_namespace(ns_job, BASE_URL + '/jdl/' + job.jobname + '/votable#')

    # Activity
    act_id = 'opus_job:' + job.jobname + '/' + job.jobid
    act = pdoc.activity(act_id, startTime=job.start_time, endTime=job.end_time)
    act.add_attributes({
        'prov:label': job.jobname,  # + '/' + job.jobid,
    })

    # Descriptions
    if descriptions:
        adescid = '#' + job.jobname + "#description"
        adescbundle = pdoc.bundle(adescid)
        setattr(adescbundle, "_label", adescid)
        # ActivityDescription
        adesc = adescbundle.activityDescription('opus_jdl:' + job.jobname, job.jobname)
        adesc.add_attributes({
            'prov:label': job.jobname,
        })
        pdoc.isDescribedBy(act, adesc)  #, other_attributes={
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

        if descriptions > 1:
            # UsageDescription
            uds = []
            for ename, edict in job.jdl.content.get('used', {}).items():
                ed = ""
                edattrs = {}
                for ekey, evalue in edict.items():
                    if evalue and ekey not in ['default']:
                        if evalue:
                            if ekey == 'content_type':
                                # EntityDescription
                                ed = 'media-type:' + evalue
                                pdoc.entityDescription(ed, evalue, other_attributes={'prov:label': evalue})
                            elif ekey == 'annotation':
                                edattrs['voprov:description'] = evalue
                            else:
                                edattrs['voprov:' + ekey] = evalue
                edattrs['prov:label'] = ename
                uds.append(adescbundle.usageDescription('opus_jdl:' + job.jobname + '#' + ename, adesc, ename))
                uds[-1].add_attributes(edattrs)
                if ed:
                    pdoc.isRelatedTo(ed, uds[-1])
            # GenerationDescription
            gds = []
            for ename, edict in job.jdl.content.get('generated', {}).items():
                ed = ""
                edattrs = {}
                for ekey, evalue in edict.items():
                    if evalue and ekey not in ['default']:
                        if evalue:
                            if ekey == 'content_type':
                                # EntityDescription
                                ed = 'media-type:' + evalue
                                pdoc.entityDescription(ed, evalue, other_attributes={'prov:label': evalue})
                            elif ekey == 'annotation':
                                edattrs['voprov:description'] = evalue
                            else:
                                edattrs['voprov:' + ekey] = evalue
                edattrs['prov:label'] = ename
                gds.append(adescbundle.generationDescription('opus_jdl:' + job.jobname + '#' + ename, adesc, ename))
                gds[-1].add_attributes(edattrs)
                if ed:
                    pdoc.isRelatedTo(ed, gds[-1])
            # Configuration descriptions
            if configuration:
                # ParameterDescription
                pds = []
                for pname, pdict in job.jdl.content.get('parameters', {}).items():
                    pdattrs = {}
                    for pkey, pvalue in pdict.items():
                        if pvalue:
                            if pkey == 'annotation':
                                pdattrs['voprov:description'] = pvalue
                            else:
                                pdattrs['voprov:' + pkey] = pvalue
                    pdattrs['prov:label'] = pname
                    pdname = 'opus_jdl:' + job.jobname + '#' + pname
                    pds.append(adescbundle.parameterDescription(pdname, adesc, pname, pdict.get('type', 'char')))
                    pds[-1].add_attributes(pdattrs)

        # Agent: contact for the job in ActivityDescription
        if agents:
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
                # Link to ActivityDescription
                pdoc.influence(adesc, contact, other_attributes={
                    'prov:role': 'contact'
                })

    # Agent: owner of the job
    if agents:
        owner = pdoc.agent('opus_user:' + job.owner)
        owner.add_attributes({
            'prov:label': job.owner,
            #'foaf:name': job.owner,
        })
        act.wasAssociatedWith(owner, attributes={
            'prov:role': 'owner'
        })

    # Parameters
    if configuration:
        # Add Parameter Collection?
        # all_params = pdoc.collection('opus_job:' + job.jobname + '/' + job.jobid + '/parameters')
        aconfid = '#' + job.jobid + '#configuration'  # + '/' + job.jobid + '/parameters'
        aconfbundle = pdoc.bundle(aconfid)
        setattr(aconfbundle, "_label", aconfid)
        params = []
        for pname, pdict in job.jdl.content.get('parameters', {}).items():
            # Add Parameter
            if pname in job.parameters:
                # the parameter was defined for this activity
                value = job.parameters[pname]['value']
            else:
                # the default value was used
                value = pdict['default']
            str_value = str(value)
            show_value = (str_value[:25] + '...') if len(str_value) > 25 else str_value
            pattrs = {
                'prov:label': pname + " = " + show_value,
            }
            params.append(aconfbundle.parameter('opus_job:' + job.jobname + '/' + job.jobid + '/parameters/' + pname, pname, value))
            params[-1].add_attributes(pattrs)
            # Activity-Parameter relation
            pdoc.wasConfiguredBy(act, params[-1], "Parameter")
            # Link to ParameterDescription
            if descriptions > 1:
                pdname = 'opus_jdl:' + job.jobname + '#' + pname
                pdoc.isDescribedBy(params[-1], pdname)
            else:
                # Add attributes to the parameter directly
                pdattrs = {}
                for pkey, pvalue in pdict.items():
                    if pvalue:
                        if pkey == 'annotation':
                            pdattrs['voprov:description'] = pvalue
                        else:
                            pdattrs['voprov:' + pkey] = pvalue
                params[-1].add_attributes(pdattrs)
            # Member of Collection
            # all_params.hadMember(params[-1])
        # Activity-Collection relation
        # pdoc.influence(act, all_params)
        logger.debug(pdoc._bundles)

    # Used entities
    used_entities = []
    if (depth != 0 and direction == 'BACK') or show_used:
        # Explore used entities for the activity if depth > 0
        e_in = []
        for pname, pdict in job.jdl.content.get('used', {}).items():
            # Look for value and entity record and get pqn (local id)
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
            # For each entity corresponding to this role
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
                # Link to description
                ed = ""
                if 'content_type' in pdict:
                    ed = 'media-type:' + pdict['content_type']
                if descriptions > 1 and ed:
                    pdoc.isDescribedBy(pqn, ed)
                # Explores entity origin if known entity and depth > 1
                if entity and depth != 1 and direction == 'BACK':
                    if depth != 1 and entity.get('jobid'):
                        other_pdocs.append(
                            job2prov(
                                entity['jobid'], job.user,
                                depth=depth-2, direction=direction, members=members, agents=agents, model=model,
                                descriptions=descriptions, configuration=configuration,
                                show_generated=True
                            )
                        )

    # Generated entities (if depth > 0)
    if (depth != 0 and direction == 'FORWARD') or show_generated:
        # Check if internal provenance is given, add as a generated bundle? or directly?
        ipfile = os.path.join(JOBDATA_PATH, jobid, INTERNAL_PROVENANCE_FILENAME)
        ipbundle = None
        if os.path.isfile(ipfile):
            ipdoc = prov.read(ipfile)
            ipid = "#" + job.jobid + "#internal_provenance"
            ipbundle = VOProvBundle(namespaces=ipdoc.namespaces, identifier=ipid)
            setattr(ipbundle, "_label", ipid)
            #inpbundle._identifier = "id:" + job.jobid + "_prov"
            ipbundle.update(ipdoc)
            #inpprov = inpdoc.bundle(job.jobid + "_prov")
            pdoc.add_bundle(ipbundle)
            pdoc.wasGeneratedBy(ipbundle.identifier, act)
            #pdoc.update(inpdoc)
            #for rec in inpdoc.get_records():
            #    if "Activity" in str(rec.get_type()):
            #        inf_act = pdoc.get_record(rec.identifier)[0]
            #        inf_act.wasInformedBy(act)
        # Add job results as entities
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
                    pdict = {}
                    if entity:
                        eattrs['prov:label'] = entity['file_name']
                        eattrs['voprov:result_name'] = entity['result_name']
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
                    # Add derivation link from internal provenance
                    if entity.get("from_entity", None) and ipbundle:
                        e_from = ipbundle.get_record(entity["from_entity"])[0]
                        e_out[-1].wasDerivedFrom(e_from)
                        #copy_act = pdoc.activity(act_id + '_copy_to_datastore', other_attributes={"prov:label": "copy_to_datastore"})
                        #copy_act.wasInformedBy(act)
                        #copy_act.used(entity["from_entity"])
                        #e_out[-1].wasGeneratedBy(copy_act)
                    # Add EntityDescription if exists
                    if pdict and descriptions > 1:
                        if 'content_type' in pdict:
                            ed = 'media-type:' + pdict['content_type']
                            pdoc.isDescribedBy(rqn, ed)
                    # Search forward for activities that used this entity
                    if entity and depth != 1 and direction == 'FORWARD':
                        used_query = job.storage.session.query(job.storage.Used).filter_by(entity_id=entity_id)
                        used_rows = used_query.all()
                        for row in used_rows:
                            other_pdocs.append(
                                job2prov(
                                    row.jobid, job.user,
                                    depth=depth-2, direction=direction, members=members, agents=agents, model=model,
                                    descriptions=descriptions, configuration=configuration,
                                    show_used=True
                                )
                            )

    # Merge all prov documents
    for opdoc in other_pdocs:
        pdoc.update(opdoc)
    pdoc = pdoc.unified()
    # Filter similar relations
    pdoc = pdoc.unified_relations()
    if w3c:
        pdoc = pdoc.get_w3c()
    return pdoc


def unified_relations(bundle):
    hash_records = []
    if bundle.is_document():
        for subbundle in bundle._bundles:
            if not hasattr(bundle._bundles[subbundle], "_label"):
                setattr(bundle._bundles[subbundle], "_label", "")
            bundle._bundles[subbundle] = unified_relations(bundle._bundles[subbundle])
    for record in bundle._records:
        if record.is_relation():
            hash_records.append(hash(str(record)))
        else:
            hash_records.append(hash(record))
    for hash_record in list(set(hash_records)):
        while hash_records.count(hash_record) > 1:
            rec_index = hash_records.index(hash_record)
            bundle._records.pop(rec_index)
            hash_records.pop(rec_index)
    return bundle


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
    Convert ProvDocument to dot graphical format then svg
    :param prov_doc:
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


def prov2png_content(prov_doc, attributes=True, direction='BT'):
    """
    Convert ProvDocument to dot graphical format then png
    :param prov_doc:
    :return:
    """
    try:
        dot = prov2dot(prov_doc, attributes=attributes, direction=direction)
        png_content = dot.create(format="png")
    except InvocationException as e:
        png_content = ""
    return png_content
