# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.model import (ProvElement, ProvBundle, ProvEntity)
from .constants import *

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'


class VOProvConfig(ProvElement):
    FORMAL_ATTRIBUTES = None
    _prov_type = None

    def get_w3c(self, bundle=None):
        if bundle is None:
            bundle = ProvBundle()
        w3c_record = ProvEntity(bundle, self.identifier, self.attributes)
        w3c_record.add_asserted_type(self.__class__.__name__)
        return bundle.add_record(w3c_record)


class VOProvConfigFile(VOProvConfig):
    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME, VOPROV_ATTR_LOCATION)
    _prov_type = VOPROV_CONFIGURATION_FILE


class VOProvParameter(VOProvConfig):
    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME, VOPROV_ATTR_VALUE)
    _prov_type = VOPROV_CONFIGURATION_PARAMETER
