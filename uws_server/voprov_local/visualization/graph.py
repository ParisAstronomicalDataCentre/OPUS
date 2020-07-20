# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.graph import *
from voprov.models.model import *

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'

INFERRED_ELEMENT_CLASS.update({
    VOPROV_ATTR_ENTITY:             VOProvEntity,
    VOPROV_ATTR_ACTIVITY:           VOProvActivity,
    VOPROV_ATTR_AGENT:              VOProvAgent,
    VOPROV_ATTR_TRIGGER:            VOProvEntity,
    VOPROV_ATTR_GENERATED_ENTITY:   VOProvEntity,
    VOPROV_ATTR_USED_ENTITY:        VOProvEntity,
    VOPROV_ATTR_DELEGATE:           VOProvAgent,
    VOPROV_ATTR_RESPONSIBLE:        VOProvAgent,
    VOPROV_ATTR_SPECIFIC_ENTITY:    VOProvEntity,
    VOPROV_ATTR_GENERAL_ENTITY:     VOProvEntity,
    VOPROV_ATTR_ALTERNATE1:         VOProvEntity,
    VOPROV_ATTR_ALTERNATE2:         VOProvEntity,
    VOPROV_ATTR_COLLECTION:         VOProvEntity,
    VOPROV_ATTR_INFORMED:           VOProvActivity,
    VOPROV_ATTR_INFORMANT:          VOProvActivity,
    VOPROV_ATTR_BUNDLE:             VOProvBundle,
    VOPROV_ATTR_PLAN:               VOProvEntity,
    VOPROV_ATTR_ENDER:              VOProvEntity,
    VOPROV_ATTR_STARTER:            VOProvEntity,
})
