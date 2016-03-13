#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Mar 10 2016

UWS v1.0 server implementation using bottle.py
See http://www.ivoa.net/documents/UWS/20101010/REC-UWS-1.0-20101010.html

@author: mservillat
"""

from prov.model import ProvDocument
import datetime

# examples:
# http://prov.readthedocs.org/en/latest/usage.html#simple-prov-document
# http://lists.g-vo.org/pipermail/prov-adhoc/2015-June/000025.html


def job2prov(job):

    # job.wadl = {
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
    # results[r.get('value')] = {
    #     'mediaType': r.get('mediaType'),
    #     'default': r.get('default'),
    #     'description': list(r)[0].text,
    # }

    pdoc = ProvDocument()
    # Declaring namespaces for various prefixes used in the example
    pdoc.add_namespace('prov', 'http://www.w3.org/ns/prov#')
    pdoc.add_namespace('voprov', 'http://www.ivoa.net/ns/voprov/')
    pdoc.add_namespace('cta', 'http://www.cta-observatory.org/ns/cta')
    pdoc.add_namespace('ctadata', 'ivo://vopdc.obspm/cta#')
    pdoc.add_namespace('uwsdata', 'https://voparis-uws-test.obspm.fr/rest/' + job.jobname + '/' + job.jobid + '/')
    pdoc.add_namespace('ctajobs', 'http://www.cta-observatory.org/ns/jobs')
    # Adding an activity
    ctbin = pdoc.activity('ctajobs:' + job.jobname, job.start_time, job.end_time)
    # TODO: add job description, version, url, ...
    # Agent
    pdoc.agent('cta:consortium', other_attributes={'prov:type': "Organization"})
    pdoc.wasAssociatedWith(ctbin, 'cta:consortium')
    # Entities, in and out with relations
    e_in = []
    for pname, pdict in job.wadl['parameters'].iteritems():
        if pname.startswith('in'):
            e_in.append(pdoc.entity('uwsdata:parameters/' + pname))
            # TODO: use publisher_did? add prov attributes, add voprov attributes?
            ctbin.used(e_in[-1])
    e_out = []
    for rname, rdict in job.wadl['results'].iteritems():
        e_out.append(pdoc.entity('uwsdata:results/' + rname))
        # TODO: use publisher_did? add prov attributes, add voprov attributes?
        e_out[-1].wasGeneratedBy(ctbin)
        for e in e_in:
            e_out[-1].wasDerivedFrom(e)
    return pdoc
