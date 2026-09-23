#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Default generators of identifiers and tokens (settings JOB_ID_GEN, ENTITY_ID_GEN, TOKEN_GEN)

Other generators can be set as import strings "module:function", e.g. in .env:
    OPUS_JOB_ID_GEN=my_generators:job_id
They must have the same signatures as below, and be defined in a module that does not
import uws_server or uws_client (the settings are loaded when those are imported).
"""

import uuid


def job_id(length):
    """Job identifier: the last `length` characters of a random uuid (length=JOB_ID_LENGTH)"""
    # uuid example: ea5caa9f-0a76-42f5-a1a7-43752df755f0
    # uuid[-12:]: 43752df755f0
    # uuid[-6:]: f755f0
    return str(uuid.uuid4())[-length:]


def entity_id(length, **kwargs):
    """Entity identifier (length=JOB_ID_LENGTH), kwargs contains all the known attributes of the entity"""
    return job_id(length)


def token(context=None):
    """Random token for a new user

    Used as a column default by SQLAlchemy, which calls it with its execution context
    """
    return str(uuid.uuid4())
