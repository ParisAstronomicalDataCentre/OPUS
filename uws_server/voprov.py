#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Export UWS job description to a ProvDocument following the W3C PROV standard
"""

from prov.model import ProvDocument
from prov.dot import prov_to_dot

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
    #     'mediaType': r.get('mediaType'),
    #     'default': r.get('default'),
    #     'description': list(r)[0].text,
    # }

    pdoc = ProvDocument()
    # Declaring namespaces for various prefixes used in the example
    pdoc.add_namespace('prov', 'http://www.w3.org/ns/prov#')
    pdoc.add_namespace('voprov', 'http://www.ivoa.net/ns/voprov#')
    pdoc.add_namespace('cta', 'http://www.cta-observatory.org#')
    pdoc.add_namespace('cta_jobs', 'http://www.cta-observatory.org#')
    ns_uws_job = 'job'
    pdoc.add_namespace(ns_uws_job, 'https://voparis-uws-test.obspm.fr/rest/' + job.jobname + '/' + job.jobid + '/#')
    ns_uws_param = 'param'
    pdoc.add_namespace(ns_uws_param, 'https://voparis-uws-test.obspm.fr/rest/' + job.jobname + '/' + job.jobid + '/parameters/')
    ns_uws_result = 'result'
    pdoc.add_namespace(ns_uws_result, 'https://voparis-uws-test.obspm.fr/rest/' + job.jobname + '/' + job.jobid + '/results/')
    # Activity
    ctbin = pdoc.activity(ns_uws_job + ':' + job.jobname, job.start_time, job.end_time)
    # TODO: add job description, version, url, ...
    # ctbin.add_attributes({
    #     'prov:label': job.jdl.content['description'],
    # })
    # Agent: CTAC
    ctac = pdoc.agent('cta:consortium')
    ctac.add_attributes({
        'prov:label': 'CTA Consortium',
        'prov:type': 'Organization',
    })
    pdoc.wasAssociatedWith(ctbin, ctac)
    # Entities, in and out with relations
    e_in = []
    act_attr = {}
    for pname, pdict in job.jdl.content['parameters'].iteritems():
        pqn = ns_uws_param + ':' + pname
        # Add some UWS parameters as input Entities
        #if pname.startswith('in'):
        if any(x in pdict['type'] for x in ['file', 'xs:anyURI']):
            e_in.append(pdoc.entity(pqn))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            e_in[-1].add_attributes({
                'prov:type': pdict['type'],
                'prov:value': job.parameters[pname]['value']
            })
            ctbin.used(e_in[-1])
        else:
            # Otherwise add UWS parameters as attributes to the Activity
            if pname in job.parameters:
                act_attr[pqn] = job.parameters[pname]['value']
            else:
                act_attr[pqn] = pdict['default']
    if len(act_attr) > 0:
        ctbin.add_attributes(act_attr)
    e_out = []
    for rname in job.results:
        if rname not in ['stdout', 'stderr', 'provjson', 'provxml', 'provsvg']:
            rdict = job.jdl.content['results'][rname]
            rqn = ns_uws_result + ':' + rname
            e_out.append(pdoc.entity(rqn))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            e_out[-1].add_attributes({
                'prov:type': rdict['mediaType'],
                'prov:value': job.results[rname]['url']
            })
            e_out[-1].wasGeneratedBy(ctbin)
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
    dot = prov2dot(prov_doc)
    svg_content = dot.create(format="svg")
    with open(fname, "w") as f:
        f.write(svg_content)
