#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
"""

from distutils.core import setup

setup(
    name='UWS Server',
    version='0.1',
    description='Job controller server and client based on the IVOA standard UWS',
    long_description='Job controller server and client developed using the micro-framework '
                     'bottle.py. The standard pattern Universal Worker System v1.0 (UWS) to '
                     'manage job execution as defined by the International Virtual Observatory '
                     'Alliance (IVOA) is implemented as a REST service.',
    author='Mathieu Servillat',
    author_email='mathieu.servillat@obspm.fr',
    license='MIT',
)
