# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.model import (ProvElement, ProvBundle, ProvEntity)
from .constants import *

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'


class VOProvDescription(ProvElement):
    """Base class for VOProvDescription classes"""
    FORMAL_ATTRIBUTES = None
    _prov_type = None

    def get_w3c(self, bundle=None):
        """get this element in the prov version which is an implementation of the W3C PROV-DM standard"""
        if bundle is None:
            bundle = ProvBundle()
        w3c_record = ProvEntity(bundle, self.identifier, self.attributes)
        w3c_record.add_asserted_type(self.__class__.__name__)
        return bundle.add_record(w3c_record)


class VOProvActivityDescription(VOProvDescription):
    """Class for VOProv activity description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME,)
    _prov_type = VOPROV_ACTIVITY_DESCRIPTION

    def set_name(self, name):
        """Set the name of this activity description.

        :param name:                    A human-readable name for the agent.
        """
        self._attributes[VOPROV_ATTR_NAME] = {name}

    def set_version(self, version):
        """Set a version for this activity description.

        :param version:                 A version number, if applicable (e.g., for the code used).
        """
        self._attributes[VOPROV['version']] = {version}

    def set_description(self, description):
        """Set a description for this activity description.

        :param description:             Additional free text describing how the activity works internally.
        """
        self._attributes[VOPROV['description']] = {description}

    def set_docurl(self, docurl):
        """Set a docurl for this activity description.

        :param docurl:                  Link to further documentation on this activity, e.g., a paper, the source code
                                        in a version control system etc.
        """
        self._attributes[VOPROV['docurl']] = {docurl}

    def set_type(self, type):
        """Set the type of this activity description.

        :param type:                    Type of the activity.
        """
        self._attributes[VOPROV['type']] = {type}

    def set_subtype(self, subtype):
        """Set a subtype for this activity description.

        :param subtype:                 More specific subtype of the activity.
        """
        self._attributes[VOPROV['subtype']] = {subtype}

    def isDescriptorOf_activity(self, activity, identifier=None):
        """
        Creates a new relation between an activity and this activity description.

        :param activity:                Identifier or object of the activity described by this activity description.
        :param identifier:              Identifier for the relation between this activity description and the activity
                                        (default: None).
        """
        return self._bundle.description(activity, self, identifier)

    def usageDescription(self, identifier, role, description=None, type=None,
                         multiplicity=None, other_attributes=None):
        """
        Creates a new usage description.

        :param identifier:              Identifier for new usage description.
        :param role:                    Function of the entity with respect to the activity.
        :param description:             A descriptive text for this kind of usage (default: None).
        :param type:                    Type of relation (default: None).
        :param multiplicity:            Number of expected input entities to be used with the given role
                                        (default: None).
        :param other_attributes:        Optional other attributes as a dictionary or list
                                        of tuples to be added to the record optionally (default: None).
        """
        return self._bundle.usageDescription(identifier, self, role, description, type, multiplicity, other_attributes)

    def generationDescription(self, identifier, role, description=None, type=None,
                              multiplicity=None, other_attributes=None):
        """
        Creates a new generation description.

        :param identifier:              Identifier for new generation description.
        :param role:                    Function of the entity with respect to the activity.
        :param description:             A descriptive text for this kind of generation (default: None).
        :param type:                    Type of relation (default: None).
        :param multiplicity:            Number of expected input entities to be generated with the given role
                                        (default: None).
        :param other_attributes:        Optional other attributes as a dictionary or list
                                        of tuples to be added to the record optionally (default: None).
        """
        return self._bundle.generationDescription(identifier, self, role, description, type,
                                                  multiplicity, other_attributes)


class VOProvGenerationDescription(VOProvDescription):
    """Class for VOProv generation description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_ROLE,)
    _prov_type = VOPROV_GENERATION_DESCRIPTION

    def set_role(self, role):
        """Set the role of this generation description.

        :param role:                    Function of the entity with respect to the activity.
        """
        self._attributes[VOPROV_ATTR_ROLE] = {role}

    def set_description(self, description):
        """Set a description for this generation description.

        :param description:             A descriptive text for this kind of generation.
        """
        self._attributes[VOPROV['description']] = {description}

    def set_type(self, type):
        """Set the type of this generation description.

        :param type:                    Type of relation.
        """
        self._attributes[VOPROV['type']] = {type}

    def set_multiplicity(self, multiplicity):
        """Set a multiplicity for this generation description.

        :param multiplicity:            Number of expected input entities to be generated with the given role.
        """
        self._attributes[VOPROV['multiplicity']] = {multiplicity}

    def isRelatedTo_entityDescription(self, entity_description, identifier=None):
        """
        Creates a new relation between this generation description and a entity description.

        :param entity_description:      The entity description related to this generation description.
        :param identifier:              Identifier for new isRelatedTo relation record (default: None).
        """
        return self._bundle.relate(self, entity_description, identifier)


class VOProvUsageDescription(VOProvDescription):
    """Class for VOProv usage description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_ROLE,)
    _prov_type = VOPROV_USAGE_DESCRIPTION

    def set_role(self, role):
        """Set the role of this usage description.

        :param role:                    Function of the entity with respect to the activity.
        """
        self._attributes[VOPROV_ATTR_ROLE] = {role}

    def set_description(self, description):
        """Set a description for this usage description.

        :param description:             A descriptive text for this kind of usage.
        """
        self._attributes[VOPROV['description']] = {description}

    def set_type(self, type):
        """Set the type of this usage description.

        :param type:                    Type of relation.
        """
        self._attributes[VOPROV['type']] = {type}

    def set_multiplicity(self, multiplicity):
        """Set a multiplicity for this usage description.

        :param multiplicity:            Number of expected input entities to be used with the given role.
        """
        self._attributes[VOPROV['multiplicity']] = {multiplicity}

    def isRelatedTo_entityDescription(self, entity_description, identifier=None):
        """
        Creates a new relation between this usage description and an entity description.

        :param entity_description:      The entity description related to this usage description.
        :param identifier:              Identifier for new isRelatedTo relation record (default: None).
        """
        return self._bundle.relate(self, entity_description, identifier)


class VOProvEntityDescription(VOProvDescription):
    """Base class for VOProv entity description classes"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME,)
    _prov_type = VOPROV_ENTITY_DESCRIPTION

    def set_name(self, name):
        """Set the role of this usage description.

        :param name:                    A human-readable name for the entity description.
        """
        self._attributes[VOPROV_ATTR_NAME] = {name}

    def set_description(self, description):
        """Set a description for this entity description.

        :param description:             A descriptive text for this kind of entity.
        """
        self._attributes[VOPROV['description']] = {description}

    def set_docurl(self, docurl):
        """Set a docurl for this entity description.

        :param docurl:                  Link to more documentation.
        """
        self._attributes[VOPROV['docurl']] = {docurl}

    def set_type(self, type):
        """Set the type of this entity description.

        :param type:                    Type of the entity.
        """
        self._attributes[VOPROV['type']] = {type}

    def isDescriptorOf_entity(self, entity, identifier=None):
        """
        Creates a new relation between an entity and this entity description.

        :param entity:                  The entity described by this entity description.
        :param identifier:              Identifier for new isDescribedBy relation record (default: None).
        """
        return self._bundle.description(entity, self, identifier)

    def isRelatedTo_usageDescription(self, usage_description, identifier=None):
        """
        Creates a new relation between an usage description and this entity description.

        :param usage_description:       The usage description related to this entity description.
        :param identifier:              Identifier for new isRelatedTo relation record (default: None).
        """
        return self._bundle.relate(usage_description, self, identifier)

    def isRelatedTo_generationDescription(self, generation_description, identifier=None):
        """
        Creates a new relation between a generation description and this entity description.

        :param generation_description:  The generation description related to this entity description.
        :param identifier:              Identifier for new isRelatedTo relation record (default: None).
        """
        return self._bundle.relate(generation_description, self, identifier)


class VOProvValueDescription(VOProvEntityDescription):
    """Class for VOProv value entity description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME, VOPROV_ATTR_VALUE_TYPE)
    _prov_type = VOPROV_VALUE_DESCRIPTION

    def set_valueType(self, valueType):
        """Set the value type of this value description.

        :param valueType:               Description of a value from a combination of datatype, arraysize and xtype
                                        following VOTable 1.3.
        """
        self._attributes[VOPROV_ATTR_VALUE_TYPE] = {valueType}

    def set_unit(self, unit):
        """Set the unit of this value description.

        :param unit:                    FVO unit, see C.1.1 and Derriere and Gray et al. (2014) for recommended unit
                                        representation.
        """
        self._attributes[VOPROV['unit']] = {unit}

    def set_ucd(self, ucd):
        """Set the ucd of this value description.

        :param ucd:                     Unified Content Descriptor, supplying a standardized classification of the
                                        physical quantity.
        """
        self._attributes[VOPROV['ucd']] = {ucd}

    def set_uType(self, uType):
        """Set the utype of this value description.

        :param uType:                   Utype, meant to express the role of the value in the context of an external
                                        data model.
        """
        self._attributes[VOPROV['uType']] = {uType}


class VOProvDataSetDescription(VOProvEntityDescription):
    """Class for VOProv data set entity description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME, VOPROV_ATTR_CONTENT_TYPE)
    _prov_type = VOPROV_DATASET_DESCRIPTION

    def set_contentType(self, contentType):
        """Set the type of content of this dataset description.

        :param contentType:             Format of the dataset, MIME type when applicable.
        """
        self._attributes[VOPROV_ATTR_CONTENT_TYPE] = {contentType}


class VOProvConfigFileDescription(VOProvDescription):
    """Class for VOProv configuration file description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME, VOPROV_ATTR_CONTENT_TYPE)
    _prov_type = VOPROV_CONFIG_FILE_DESCRIPTION


class VOProvParameterDescription(VOProvDescription):
    """Class for VOProv parameter description"""

    FORMAL_ATTRIBUTES = (VOPROV_ATTR_NAME, VOPROV_ATTR_VALUE_TYPE)
    _prov_type = VOPROV_PARAMETER_DESCRIPTION
