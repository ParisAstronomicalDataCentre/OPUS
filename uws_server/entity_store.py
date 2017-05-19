#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2017 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Defines class to store and keep track of entities
"""

import hashlib
from settings import *

class EntityStore(object):

    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    def __init__(self, path=ENTITY_STORE_PATH):
        # PATHs
        self.path = path

    def get_hash(self, fname):
        sha1 = hashlib.sha1()
        with open(fname, 'rb') as f:
            while True:
                data = f.read(self.BUF_SIZE)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()

