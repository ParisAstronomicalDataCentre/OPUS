# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.dot import *
from voprov.visualization.graph import *

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'

# updating the generic node style map which is used when the object used in a relation is not declared
GENERIC_NODE_STYLE.update({
    # extension of prov model
    VOProvEntity: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvActivity: {
        'shape': 'box', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvAgent: {
        'shape': 'house', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvBundle: {
        'shape': 'folder', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },

    # voprov description
    VOProvDescription: {
        'shape': 'star', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'blue'
    },
    VOProvActivityDescription: {
        'shape': 'box', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvEntityDescription: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvUsageDescription: {
        'shape': 'invtrapezium', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvGenerationDescription: {
        'shape': 'trapezium', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvConfigFileDescription: {
        'shape': 'trapezium', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvParameterDescription: {
        'shape': 'trapezium', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },

    # voprov configuration
    VOProvConfigFile: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
    VOProvParameter: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': 'lightgray', 'color': 'dimgray'
    },
})

# updating the style of the different prov record
DOT_PROV_STYLE.update({
    # extend prov model
    # Elements
    VOPROV_ENTITY: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': '#FFFC87', 'color': '#808080'
    },
    VOPROV_VALUE_ENTITY: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': '#FFFC87', 'color': '#808080'
    },
    VOPROV_DATASET_ENTITY: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': '#FFFC87', 'color': '#808080'
    },
    VOPROV_ACTIVITY: {
        'shape': 'box', 'style': 'filled',
        'fillcolor': '#9FB1FC', 'color': '#0000FF'
    },
    VOPROV_AGENT: {
        'shape': 'house', 'style': 'filled',
        'fillcolor': '#FED37F'
    },
    VOPROV_BUNDLE: {
        'shape': 'folder', 'style': 'filled',
        'fillcolor': 'aliceblue'
    },
    # Relations
    VOPROV_GENERATION: {
        'label': 'wasGeneratedBy', 'fontsize': '10.0',
        'color': 'darkgreen', 'fontcolor': 'darkgreen'
    },
    VOPROV_USAGE: {
        'label': 'used', 'fontsize': '10.0',
        'color': 'red4', 'fontcolor': 'red'
    },
    VOPROV_COMMUNICATION: {
        'label': 'wasInformedBy', 'fontsize': '10.0'
    },
    VOPROV_START: {
        'label': 'wasStartedBy', 'fontsize': '10.0'
    },
    VOPROV_END: {
        'label': 'wasEndedBy', 'fontsize': '10.0'
    },
    VOPROV_INVALIDATION: {
        'label': 'wasInvalidatedBy', 'fontsize': '10.0'
    },
    VOPROV_DERIVATION: {
        'label': 'wasDerivedFrom', 'fontsize': '10.0'
    },
    VOPROV_ATTRIBUTION: {
        'label': 'wasAttributedTo', 'fontsize': '10.0',
        'color': '#FED37F'
    },
    VOPROV_ASSOCIATION: {
        'label': 'wasAssociatedWith', 'fontsize': '10.0',
        'color': '#FED37F'
    },
    VOPROV_DELEGATION: {
        'label': 'actedOnBehalfOf', 'fontsize': '10.0',
        'color': '#FED37F'
    },
    VOPROV_INFLUENCE: {
        'label': 'wasInfluencedBy', 'fontsize': '10.0',
        'color': 'grey'
    },
    VOPROV_ALTERNATE: {
        'label': 'alternateOf', 'fontsize': '10.0'
    },
    VOPROV_SPECIALIZATION: {
        'label': 'specializationOf', 'fontsize': '10.0'
    },
    VOPROV_MENTION: {
        'label': 'mentionOf', 'fontsize': '10.0'
    },
    VOPROV_MEMBERSHIP: {
        'label': 'hadMember', 'fontsize': '10.0'
    },

    # voprov description
    VOPROV_ACTIVITY_DESCRIPTION: {
        'shape': 'box', 'style': 'filled',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_USAGE_DESCRIPTION: {
        'shape': 'invtrapezium', 'style': 'filled', 'margin': '0 0', 'fixedsize': 'false',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_GENERATION_DESCRIPTION: {
        'shape': 'trapezium', 'style': 'filled', 'margin': '0 0', 'fixedsize': 'false',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_ENTITY_DESCRIPTION: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_VALUE_DESCRIPTION: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_DATASET_DESCRIPTION: {
        'shape': 'oval', 'style': 'filled',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_CONFIG_FILE_DESCRIPTION: {
        'shape': 'box3d', 'style': 'filled',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },
    VOPROV_PARAMETER_DESCRIPTION: {
        'shape': 'note', 'style': 'filled',
        'fillcolor': '#FF7C47', 'color': '#808080'
    },

    # voprov configuration
    VOPROV_CONFIGURATION_FILE: {
        'shape': 'box3d', 'style': 'filled',
        'fillcolor': '#4CDD4C', 'color': '#808080'
    },
    VOPROV_CONFIGURATION_PARAMETER: {
        'shape': 'note', 'style': 'filled',
        'fillcolor': '#4CDD4C', 'color': '#808080'
    },

    # voprov relation
    VOPROV_DESCRIPTION_RELATION: {
        'label': 'isDescribedBy', 'fontsize': '10.0',
        'color': '#FF6629', 'fontcolor': '#FF6629'
    },
    VOPROV_RELATED_TO_RELATION: {
        'label': 'isRelatedTo', 'fontsize': '10.0',
        'color': '#BFC9BF', 'fontcolor': '#BFC9BF'
    },
    VOPROV_CONFIGURATION_RELATION: {
        'label': 'wasConfiguredBy', 'fontsize': '10.0',
        'color': '#57B857', 'fontcolor': '#57B857'
    },
    VOPROV_REFERENCE_RELATION: {
        'label': 'hadReference', 'fontsize': '10.0',
        'color': '#57B857', 'fontcolor': '#57B857'
    },
})
