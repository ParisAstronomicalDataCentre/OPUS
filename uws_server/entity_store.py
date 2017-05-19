#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2017 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Defines class to store and keep track of entities
"""

import hashlib
from storage import *
from settings import *

# TODO: move to storage.py to complete the Storage classes

class EntityStore(object):

    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    def __init__(self, path=ENTITY_STORE_PATH):
        # PATHs
        self.path = path

    def get_hash(self, fname):
        """Generate SHA1 hassh for given file
        :param fname:
        :return: hax hash
        """
        sha1 = hashlib.sha1()
        with open(fname, 'rb') as f:
            while True:
                data = f.read(self.BUF_SIZE)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()

    def get_properties(self, id):
        """get entity properties using its id
        """
        pass

    def exists(self):
        """Check if entity exists in the Store, returns entity id
        """
        pass

    def add(self):
        """Add entity to the Store
        """
        pass

    def delete(self):
        """Delete entity from the Store
        """
        pass


class SQLiteEntityStore(SQLiteStorage, EntityStore):
    pass
