# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.model import (ProvRelation, ProvBundle, ProvInfluence)
from voprov.models.constants import *

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'


class VOProvRelation(ProvRelation):
    FORMAL_ATTRIBUTES = None
    _prov_type = None

    def get_w3c(self, bundle=None):
        """get this relation in the prov version which is an implementation of the W3C PROV-DM standard"""
        if bundle is None:
            bundle = ProvBundle()
        attribute = self.extra_attributes
        relation_formal_attribute = self.formal_attributes[0:2]

        w3c_record = ProvInfluence(bundle, self.identifier, attribute)
        namespaces = [list(i) for i in w3c_record.formal_attributes]
        for i in range(0, 2):
            namespaces[i][1] = relation_formal_attribute[i][1]
        w3c_record.add_attributes(namespaces)
        w3c_record.add_asserted_type(self.__class__.__name__)
        return bundle.add_record(w3c_record)


class VOProvIsDescribedBy(VOProvRelation):
    FORMAL_ATTRIBUTES = (VOPROV_ATTR_DESCRIBED, VOPROV_ATTR_DESCRIPTOR)
    _prov_type = VOPROV_DESCRIPTION_RELATION


class VOProvIsRelatedTo(VOProvRelation):
    FORMAL_ATTRIBUTES = (VOPROV_ATTR_RELATED, VOPROV_ATTR_RELATOR)
    _prov_type = VOPROV_RELATED_TO_RELATION


class VOProvWasConfiguredBy(VOProvRelation):
    FORMAL_ATTRIBUTES = (VOPROV_ATTR_CONFIGURED, VOPROV_ATTR_CONFIGURATOR, VOPROV_ATTR_ARTEFACT_TYPE)
    _prov_type = VOPROV_CONFIGURATION_RELATION


class VOProvHadReference(VOProvRelation):
    FORMAL_ATTRIBUTES = (VOPROV_ATTR_REFERENCED, VOPROV_ATTR_REFERRER)
    _prov_type = VOPROV_REFERENCE_RELATION
