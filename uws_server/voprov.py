#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Export UWS job description to a ProvDocument following the W3C PROV standard
"""

from prov.model import ProvDocument
from prov.dot import prov_to_dot
from pydotplus.graphviz import InvocationException

# examples:
# http://prov.readthedocs.org/en/latest/usage.html#simple-prov-document
# http://lists.g-vo.org/pipermail/prov-adhoc/2015-June/000025.html


def job2prov(job):
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
    # Declaring namespaces for various prefixes used in the example
    pdoc.set_default_namespace('https://voparis-uws-test.obspm.fr/get_jdl/' + job.jobname + '/#')
    pdoc.add_namespace('prov', 'http://www.w3.org/ns/prov#')
    pdoc.add_namespace('voprov', 'http://www.ivoa.net/documents/dm/provdm/voprov#')
    pdoc.add_namespace('ctao', 'http://www.cta-observatory.org#')
    ns_uws_job = job.jobname
    pdoc.add_namespace(ns_uws_job, 'https://voparis-uws-test.obspm.fr/get_jdl/' + job.jobname + '/#')
    # Activity
    job = pdoc.activity(ns_uws_job + ':' + job.jobid, job.start_time, job.end_time)
    # TODO: add job description, version, url, ...
    job.add_attributes({
        # 'prov:label': job.jdl.content['description'],
        'voprov:location': job.jdl.content.get('url'),
        'contact_name': job.jdl.content.get('contact_name'),
        'contact_email': job.jdl.content.get('contact_email'),
    })
    # Agent: owner of the job
    agent = pdoc.agent('org:' + job.owner)
    # ctac.add_attributes({
    #     'prov:label': 'CTA Consortium',
    #     'prov:type': 'Organization',
    # })
    pdoc.wasAssociatedWith(job, agent)
    # Entities, in and out with relations
    e_in = []
    act_attr = {}
    for pname, pdict in job.jdl.content['parameters'].iteritems():
        pqn = ns_uws_job + ':' + pname
        # Add some UWS parameters as input Entities
        #if pname.startswith('in'):
        if any(x in pdict['datatype'] for x in ['file', 'xs:anyURI']):
            e_in.append(pdoc.entity(pqn))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            e_in[-1].add_attributes({
                'voprov:type': pdict['datatype'],
                #'prov:location': job.parameters[pname]['value']
            })
            job.used(e_in[-1])
        else:
            # Otherwise add UWS parameters as attributes to the Activity
            if pname in job.parameters:
                act_attr[pqn] = job.parameters[pname]['value']
            else:
                act_attr[pqn] = pdict['default']
    if len(act_attr) > 0:
        job.add_attributes(act_attr)
    e_out = []
    for rname in job.results:
        if rname not in ['stdout', 'stderr', 'provjson', 'provxml', 'provsvg']:
            rdict = job.jdl.content['results'][rname]
            rqn = ns_uws_job + ':' + rname
            e_out.append(pdoc.entity(rqn))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            e_out[-1].add_attributes({
                'voprov:type': rdict['content_type'],
                #'prov:location': job.results[rname]['url']
            })
            e_out[-1].wasGeneratedBy(job)
            for e in e_in:
                e_out[-1].wasDerivedFrom(e)
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
    dot = prov_to_dot(prov_doc)
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
    with open(fname, "w") as f:
        f.write(svg_content)
