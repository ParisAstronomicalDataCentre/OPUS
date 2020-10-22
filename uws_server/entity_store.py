#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Defines class to store and keep track of entities
"""

import hashlib
from .storage import *
from .settings import *


class EntityStore(object):

    def __init__(self, path=ENTITY_STORE_PATH):
        # PATHs
        self.path = path

    def get_file_hash(self, fname):
        """Generate SHA1 hassh for given file
        :param fname:
        :return: hax hash
        """
        BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
        sha1 = hashlib.sha1()
        with open(fname, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()

    def get_entity_properties(self, id):
        """get entity properties using its id
        :return: dict with propeties
        """
        return {}

    def entity_exists(self):
        """Check if entity exists in the Store, returns entity id
        :return: entity id
        """
        return 0

    def entity_add(self):
        """Add entity to the Store
        :return: entity id
        """
        return 0

    def entity_delete(self):
        """Delete entity from the Store
        """
        pass


class SQLEntityStore(EntityStore):

    def get_entity_properties(self, id):
        """get entity properties using its id
        :return: dict with properties
        """
        return {}

    def entity_exists(self, id=None, name=None, hash=None):
        """Check if entity exists in the Store, returns entity id
        :return: entity id
        """
        if id:
            pass
        if name:
            pass
        if hash:
            pass
        return 0

    def entity_add(self):
        """Add entity to the Store
        :return: entity id
        """
        return 0

    def entity_delete(self):
        """Delete entity from the Store
        """
        pass

