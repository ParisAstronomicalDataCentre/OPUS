# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.constants import *
from prov.model import Literal

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'


VOPROV = Namespace('voprov', 'http://www.ivoa.net/documents/ProvenanceDM/index.html#')

# Part 1 : namespace for voprov classes
# extend prov model
VOPROV_ACTIVITY =                       VOPROV['Activity']
VOPROV_ENTITY =                         VOPROV['Entity']
VOPROV_VALUE_ENTITY =                   VOPROV['ValueEntity']
VOPROV_DATASET_ENTITY =                 VOPROV['DatasetEntity']
VOPROV_GENERATION =                     VOPROV['Generation']
VOPROV_USAGE =                          VOPROV['Usage']
VOPROV_COMMUNICATION =                  VOPROV['Communication']
VOPROV_START =                          VOPROV['Start']
VOPROV_END =                            VOPROV['End']
VOPROV_INVALIDATION =                   VOPROV['Invalidation']
VOPROV_AGENT =                          VOPROV['Agent']
VOPROV_ATTRIBUTION =                    VOPROV['Attribution']
VOPROV_ASSOCIATION =                    VOPROV['Association']
VOPROV_DELEGATION =                     VOPROV['Delegation']
VOPROV_INFLUENCE =                      VOPROV['Influence']
VOPROV_DERIVATION =                     VOPROV['Derivation']
VOPROV_BUNDLE =                         VOPROV['Bundle']
VOPROV_ALTERNATE =                      VOPROV['Alternate']
VOPROV_SPECIALIZATION =                 VOPROV['Specialization']
VOPROV_MENTION =                        VOPROV['Mention']
VOPROV_MEMBERSHIP =                     VOPROV['Membership']
#   voprov description
VOPROV_ACTIVITY_DESCRIPTION =           VOPROV['ActivityDescription']
VOPROV_USAGE_DESCRIPTION =              VOPROV['UsageDescription']
VOPROV_GENERATION_DESCRIPTION =         VOPROV['GenerationDescription']
VOPROV_ENTITY_DESCRIPTION =             VOPROV['EntityDescription']
VOPROV_VALUE_DESCRIPTION =              VOPROV['ValueDescription']
VOPROV_DATASET_DESCRIPTION =            VOPROV['DatasetDescription']
VOPROV_CONFIG_FILE_DESCRIPTION =        VOPROV['ConfigFileDescription']
VOPROV_PARAMETER_DESCRIPTION =          VOPROV['ParameterDescription']
#   voprov configuration
VOPROV_CONFIGURATION_FILE =             VOPROV['ConfigFile']
VOPROV_CONFIGURATION_PARAMETER =        VOPROV['Parameter']
#   voprov relation
VOPROV_DESCRIPTION_RELATION =           VOPROV['DescriptionRelation']
VOPROV_RELATED_TO_RELATION =            VOPROV['RelatedToRelation']
VOPROV_CONFIGURATION_RELATION =         VOPROV['ConfigurationRelation']
VOPROV_REFERENCE_RELATION =             VOPROV['HadReference']


# Part 2 : map for serialization usage
#   adding the voprov provn representation for the map for provn representation
PROV_N_MAP.update({
    # extend prov model
    VOPROV_ENTITY:                      u'entity',
    VOPROV_VALUE_ENTITY:                u'valueEntity',
    VOPROV_DATASET_ENTITY:              u'datasetEntity',
    VOPROV_ACTIVITY:                    u'activity',
    VOPROV_GENERATION:                  u'wasGeneratedBy',
    VOPROV_USAGE:                       u'used',
    VOPROV_COMMUNICATION:               u'wasInformedBy',
    VOPROV_START:                       u'wasStartedBy',
    VOPROV_END:                         u'wasEndedBy',
    VOPROV_INVALIDATION:                u'wasInvalidatedBy',
    VOPROV_DERIVATION:                  u'wasDerivedFrom',
    VOPROV_AGENT:                       u'agent',
    VOPROV_ATTRIBUTION:                 u'wasAttributedTo',
    VOPROV_ASSOCIATION:                 u'wasAssociatedWith',
    VOPROV_DELEGATION:                  u'actedOnBehalfOf',
    VOPROV_INFLUENCE:                   u'wasInfluencedBy',
    VOPROV_ALTERNATE:                   u'alternateOf',
    VOPROV_SPECIALIZATION:              u'specializationOf',
    VOPROV_MENTION:                     u'mentionOf',
    VOPROV_MEMBERSHIP:                  u'hadMember',
    VOPROV_BUNDLE:                      u'bundle',

    # voprov description
    VOPROV_ACTIVITY_DESCRIPTION:        u'activityDescription',
    VOPROV_USAGE_DESCRIPTION:           u'usageDescription',
    VOPROV_GENERATION_DESCRIPTION:      u'generationDescription',
    VOPROV_ENTITY_DESCRIPTION:          u'entityDescription',
    VOPROV_VALUE_DESCRIPTION:           u'valueDescription',
    VOPROV_DATASET_DESCRIPTION:         u'datasetDescription',
    VOPROV_CONFIG_FILE_DESCRIPTION:     u'configFileDescription',
    VOPROV_PARAMETER_DESCRIPTION:       u'parameterDescription',

    # voprov configuration
    VOPROV_CONFIGURATION_FILE:          u'configFile',
    VOPROV_CONFIGURATION_PARAMETER:     u'parameter',

    # voprov relation
    VOPROV_DESCRIPTION_RELATION:        u'isDescribedBy',
    VOPROV_RELATED_TO_RELATION:         u'isRelatedTo',
    VOPROV_CONFIGURATION_RELATION:      u'wasConfiguredBy',
    VOPROV_REFERENCE_RELATION:          u'hadReference',
})

#   adding records for the map of record defined as subtypes in PROV-N but top level types in for example
#   PROV XML also need a mapping.
ADDITIONAL_N_MAP.update({
    VOPROV['Revision']:                 u'wasRevisionOf',
    VOPROV['Quotation']:                u'wasQuotedFrom',
    VOPROV['PrimarySource']:            u'hadPrimarySource',
    VOPROV['SoftwareAgent']:            u'softwareAgent',
    VOPROV['Person']:                   u'person',
    VOPROV['Organization']:             u'organization',
    VOPROV['Plan']:                     u'plan',
    VOPROV['Collection']:               u'collection',
    VOPROV['EmptyCollection']:          u'emptyCollection',
})

#   adding the voprov namespace for the Map of qualified names from the PROV namespace to their base class. If it
#   has no baseclass it maps to itsself. This is needed for example for PROV
#   XML (de)serializer where extended types are used a lot.
PROV_BASE_CLS.update({
    # extend prov model
    VOPROV_ENTITY:                      VOPROV_ENTITY,
    VOPROV_VALUE_ENTITY:                VOPROV_VALUE_ENTITY,
    VOPROV_DATASET_ENTITY:              VOPROV_DATASET_ENTITY,
    VOPROV_ACTIVITY:                    VOPROV_ACTIVITY,
    VOPROV_GENERATION:                  VOPROV_GENERATION,
    VOPROV_USAGE:                       VOPROV_USAGE,
    VOPROV_COMMUNICATION:               VOPROV_COMMUNICATION,
    VOPROV_START:                       VOPROV_START,
    VOPROV_END:                         VOPROV_END,
    VOPROV_INVALIDATION:                VOPROV_INVALIDATION,
    VOPROV_DERIVATION:                  VOPROV_DERIVATION,
    VOPROV['Revision']:                 VOPROV_DERIVATION,
    VOPROV['Quotation']:                VOPROV_DERIVATION,
    VOPROV['PrimarySource']:            VOPROV_DERIVATION,
    VOPROV_AGENT:                       VOPROV_AGENT,
    VOPROV['SoftwareAgent']:            VOPROV_AGENT,
    VOPROV['Person']:                   VOPROV_AGENT,
    VOPROV['Organization']:             VOPROV_AGENT,
    VOPROV_ATTRIBUTION:                 VOPROV_ATTRIBUTION,
    VOPROV_ASSOCIATION:                 VOPROV_ASSOCIATION,
    VOPROV['Plan']:                     VOPROV_ENTITY,
    VOPROV_DELEGATION:                  VOPROV_DELEGATION,
    VOPROV_INFLUENCE:                   VOPROV_INFLUENCE,
    VOPROV_ALTERNATE:                   VOPROV_ALTERNATE,
    VOPROV_SPECIALIZATION:              VOPROV_SPECIALIZATION,
    VOPROV_MENTION:                     VOPROV_MENTION,
    VOPROV['Collection']:               VOPROV_ENTITY,
    VOPROV['EmptyCollection']:          VOPROV_ENTITY,
    VOPROV_MEMBERSHIP:                  VOPROV_MEMBERSHIP,
    VOPROV_BUNDLE:                      VOPROV_ENTITY,

    # voprov description
    VOPROV_ACTIVITY_DESCRIPTION:        VOPROV_ACTIVITY_DESCRIPTION,
    VOPROV_USAGE_DESCRIPTION:           VOPROV_USAGE_DESCRIPTION,
    VOPROV_GENERATION_DESCRIPTION:      VOPROV_GENERATION_DESCRIPTION,
    VOPROV_ENTITY_DESCRIPTION:          VOPROV_ENTITY_DESCRIPTION,
    VOPROV_VALUE_DESCRIPTION:           VOPROV_VALUE_DESCRIPTION,
    VOPROV_DATASET_DESCRIPTION:         VOPROV_DATASET_DESCRIPTION,

    # voprov configuration
    VOPROV_CONFIGURATION_FILE:          VOPROV_CONFIGURATION_FILE,
    VOPROV_CONFIGURATION_PARAMETER:     VOPROV_CONFIGURATION_PARAMETER,

    # voprov relation
    VOPROV_DESCRIPTION_RELATION:        VOPROV_DESCRIPTION_RELATION,
    VOPROV_RELATED_TO_RELATION:         VOPROV_RELATED_TO_RELATION,
    VOPROV_CONFIGURATION_RELATION:      VOPROV_CONFIGURATION_RELATION,
    VOPROV_REFERENCE_RELATION:          VOPROV_REFERENCE_RELATION,
})


# Part 3 : Identifier for voprov's attributes
#   Adaptation of identifiers for PROV's attributes
VOPROV_ATTR_ENTITY =                    VOPROV['entity']
VOPROV_ATTR_ACTIVITY =                  VOPROV['activity']
VOPROV_ATTR_TRIGGER =                   VOPROV['trigger']
VOPROV_ATTR_INFORMED =                  VOPROV['informed']
VOPROV_ATTR_INFORMANT =                 VOPROV['informant']
VOPROV_ATTR_STARTER =                   VOPROV['starter']
VOPROV_ATTR_ENDER =                     VOPROV['ender']
VOPROV_ATTR_AGENT =                     VOPROV['agent']
VOPROV_ATTR_PLAN =                      VOPROV['plan']
VOPROV_ATTR_DELEGATE =                  VOPROV['delegate']
VOPROV_ATTR_RESPONSIBLE =               VOPROV['responsible']
VOPROV_ATTR_GENERATED_ENTITY =          VOPROV['generatedEntity']
VOPROV_ATTR_USED_ENTITY =               VOPROV['usedEntity']
VOPROV_ATTR_GENERATION =                VOPROV['generation']
VOPROV_ATTR_USAGE =                     VOPROV['usage']
VOPROV_ATTR_SPECIFIC_ENTITY =           VOPROV['specificEntity']
VOPROV_ATTR_GENERAL_ENTITY =            VOPROV['generalEntity']
VOPROV_ATTR_ALTERNATE1 =                VOPROV['alternate1']
VOPROV_ATTR_ALTERNATE2 =                VOPROV['alternate2']
VOPROV_ATTR_BUNDLE =                    VOPROV['bundle']
VOPROV_ATTR_INFLUENCEE =                VOPROV['influencee']
VOPROV_ATTR_INFLUENCER =                VOPROV['influencer']
VOPROV_ATTR_COLLECTION =                VOPROV['collection']
#   (some is used in description and configuration element, so in this case, they only appear in description part)
#   voprov description
VOPROV_ATTR_NAME =                      VOPROV['name']
VOPROV_ATTR_ROLE =                      VOPROV['role']
VOPROV_ATTR_VALUE_TYPE =                VOPROV['valueType']
VOPROV_ATTR_CONTENT_TYPE =              VOPROV['contentType']
#   voprov configuration
VOPROV_ATTR_LOCATION =                  VOPROV['location']
VOPROV_ATTR_VALUE =                     VOPROV['value']
VOPROV_ATTR_ARTEFACT_TYPE =             VOPROV['artefactType']

#   voprov relation
VOPROV_ATTR_DESCRIBED =                 VOPROV['described']
VOPROV_ATTR_DESCRIPTOR =                VOPROV['descriptor']
VOPROV_ATTR_RELATED =                   VOPROV['related']
VOPROV_ATTR_RELATOR =                   VOPROV['relator']
VOPROV_ATTR_CONFIGURED =                VOPROV['configured']
VOPROV_ATTR_CONFIGURATOR =              VOPROV['configurator']
VOPROV_ATTR_REFERENCED =                VOPROV['referenced']
VOPROV_ATTR_REFERRER =                  VOPROV['referrer']

#   adding the voprov identifier to the map for the qualified name of attribute
PROV_ATTRIBUTE_QNAMES.update({
    # update of prov attributes to voprov attributes
    VOPROV_ATTR_ENTITY,
    VOPROV_ATTR_ACTIVITY,
    VOPROV_ATTR_TRIGGER,
    VOPROV_ATTR_INFORMED,
    VOPROV_ATTR_INFORMANT,
    VOPROV_ATTR_STARTER,
    VOPROV_ATTR_ENDER,
    VOPROV_ATTR_AGENT,
    VOPROV_ATTR_PLAN,
    VOPROV_ATTR_DELEGATE,
    VOPROV_ATTR_RESPONSIBLE,
    VOPROV_ATTR_GENERATED_ENTITY,
    VOPROV_ATTR_USED_ENTITY,
    VOPROV_ATTR_GENERATION,
    VOPROV_ATTR_USAGE,
    VOPROV_ATTR_SPECIFIC_ENTITY,
    VOPROV_ATTR_GENERAL_ENTITY,
    VOPROV_ATTR_ALTERNATE1,
    VOPROV_ATTR_ALTERNATE2,
    VOPROV_ATTR_BUNDLE,
    VOPROV_ATTR_INFLUENCEE,
    VOPROV_ATTR_INFLUENCER,
    VOPROV_ATTR_COLLECTION,

    # voprov relation
    VOPROV_ATTR_DESCRIBED,
    VOPROV_ATTR_DESCRIPTOR,
    VOPROV_ATTR_RELATED,
    VOPROV_ATTR_RELATOR,
    VOPROV_ATTR_CONFIGURED,
    VOPROV_ATTR_CONFIGURATOR,
    VOPROV_ATTR_REFERENCED,
    VOPROV_ATTR_REFERRER,
})

VOPROV_ATTR_TIME = VOPROV['time']
VOPROV_ATTR_STARTTIME = VOPROV['startTime']
VOPROV_ATTR_ENDTIME = VOPROV['endTime']

#   adding the voprov identifier for the literals attribute
PROV_ATTRIBUTE_LITERALS.update({
    # update of prov literals to voprov literals
    VOPROV_ATTR_TIME,
    VOPROV_ATTR_STARTTIME,
    VOPROV_ATTR_ENDTIME,

    # voprov description
    Literal(VOPROV_ATTR_NAME),
    Literal(VOPROV_ATTR_ROLE),
    Literal(VOPROV_ATTR_VALUE_TYPE),
    Literal(VOPROV_ATTR_CONTENT_TYPE),

    # voprov configuration
    Literal(VOPROV_ATTR_LOCATION),
    Literal(VOPROV_ATTR_VALUE),
    Literal(VOPROV_ATTR_ARTEFACT_TYPE),
})

# Extra definition for convenience
VOPROV_TYPE = VOPROV['type']
VOPROV_LABEL = VOPROV['label']
VOPROV_VALUE = VOPROV['value']
VOPROV_LOCATION = VOPROV['location']
VOPROV_ROLE = VOPROV['role']

VOPROV_QUALIFIEDNAME = VOPROV['QUALIFIED_NAME']
