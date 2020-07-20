# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from prov.serializers.provxml import *
from voprov.models.constants import *

# Create a dictionary containing all top-level PROV XML elements for an easy
# mapping.
FULL_NAMES_MAP = dict(PROV_N_MAP)
FULL_NAMES_MAP.update(ADDITIONAL_N_MAP)
# Inverse mapping.
FULL_PROV_RECORD_IDS_MAP = dict((FULL_NAMES_MAP[rec_type_id], rec_type_id) for
                                rec_type_id in FULL_NAMES_MAP)


class VOProvXMLSerializer(ProvXMLSerializer):
    """PROV-XML serializer for :class:`~voprov.models.model.VOProvDocument`
    """
    def serialize(self, stream, force_types=False, **kwargs):
        """
        Serializes a :class:`~voprov.models.model.VOProvDocument` instance to `PROV-XML
        <http://www.w3.org/TR/prov-xml/>`_.

        :param stream: Where to save the output.
        :type force_types: boolean, optional
        :param force_types: Will force xsd:types to be written for most
            attributes mainly PROV-"attributes", e.g. tags not in the
            PROV namespace. Off by default meaning xsd:type attributes will
            only be set for prov:type, prov:location, and prov:value as is
            done in the official PROV-XML specification. Furthermore the
            types will always be set if the Python type requires it. False
            is a good default and it should rarely require changing.
        """
        xml_root = self.serialize_bundle(bundle=self.document,
                                         force_types=force_types)
        for bundle in self.document.bundles:
            self.serialize_bundle(bundle=bundle, element=xml_root,
                                  force_types=force_types)
        # No encoding must be specified when writing to String object which
        # does not have the concept of an encoding as it should already
        # represent unicode code points.
        et = etree.ElementTree(xml_root)
        if isinstance(stream, io.TextIOBase):
            stream.write(etree.tostring(et, xml_declaration=True,
                                        pretty_print=True).decode('utf-8'))
        else:
            et.write(stream, pretty_print=True, xml_declaration=True,
                     encoding="UTF-8")

    def serialize_bundle(self, bundle, element=None, force_types=False):
        """
        Serializes a bundle or document to PROV XML.

        :param bundle: The bundle or document.
        :param element: The XML element to write to. Will be created if None.
        :type force_types: boolean, optional
        :param force_types: Will force xsd:types to be written for most
            attributes mainly PROV-"attributes", e.g. tags not in the
            PROV namespace. Off by default meaning xsd:type attributes will
            only be set for prov:type, prov:location, and prov:value as is
            done in the official PROV-XML specification. Furthermore the
            types will always be set if the Python type requires it. False
            is a good default and it should rarely require changing.
        """
        # Build the namespace map for lxml and attach it to the root XML
        # element. No dictionary comprehension in Python 2.6!
        nsmap = dict((ns.prefix, ns.uri) for ns in
                     self.document._namespaces.get_registered_namespaces())
        if self.document._namespaces._default:
            nsmap[None] = self.document._namespaces._default.uri
        for namespace in bundle.namespaces:
            if namespace not in nsmap:
                nsmap[namespace.prefix] = namespace.uri

        for key, value in DEFAULT_NAMESPACES.items():
            uri = value.uri
            if value.prefix == "xsd":
                # The XSD namespace for some reason has no hash at the end
                # for PROV XML, but for all other serializations it does.
                uri = uri.rstrip("#")
            nsmap[value.prefix] = uri

        if element is not None:
            xml_bundle_root = etree.SubElement(
                element, _ns_prov("bundleContent"), nsmap=nsmap)
        else:
            xml_bundle_root = etree.Element(_ns_prov("document"), nsmap=nsmap)

        if bundle.identifier:
            xml_bundle_root.attrib[_ns_prov("id")] = \
                six.text_type(bundle.identifier)

        for record in bundle._records:
            rec_type = record.get_type()
            identifier = six.text_type(record._identifier) \
                if record._identifier else None

            if identifier:
                attrs = {_ns_prov("id"): identifier}
            else:
                attrs = None

            # Derive the record label from its attributes which is sometimes
            # needed.
            attributes = list(record.attributes)
            rec_label = self._derive_record_label(rec_type, attributes)

            elem = etree.SubElement(xml_bundle_root,
                                    _ns_prov(rec_label), attrs)

            for attr, value in sorted_attributes(rec_type, attributes):
                subelem = etree.SubElement(
                    elem, _ns(attr.namespace.uri, attr.localpart))
                if isinstance(value, prov.model.Literal):
                    if value.datatype not in \
                            [None, PROV["InternationalizedString"]]:
                        subelem.attrib[_ns_xsi("type")] = "%s:%s" % (
                            value.datatype.namespace.prefix,
                            value.datatype.localpart)
                    if value.langtag is not None:
                        subelem.attrib[_ns_xml("lang")] = value.langtag
                    v = value.value
                elif isinstance(value, prov.model.QualifiedName):
                    if attr not in PROV_ATTRIBUTE_QNAMES:
                        subelem.attrib[_ns_xsi("type")] = "xsd:QName"
                    v = six.text_type(value)
                elif isinstance(value, datetime.datetime):
                    v = value.isoformat()
                else:
                    v = six.text_type(value)

                # xsd type inference.
                #
                # This is a bit messy and there are all kinds of special
                # rules but it appears to get the job done.
                #
                # If it is a type element and does not yet have an
                # associated xsi type, try to infer it from the value.
                # The not startswith("prov:") check is a little bit hacky to
                # avoid type interference when the type is a standard prov
                # type.
                #
                # To enable a mapping of Python types to XML and back,
                # the XSD type must be written for these types.
                ALWAYS_CHECK = [bool, datetime.datetime, float,
                                prov.identifier.Identifier]
                # Add long and int on Python 2, only int on Python 3.
                ALWAYS_CHECK.extend(six.integer_types)
                ALWAYS_CHECK = tuple(ALWAYS_CHECK)
                if (force_types or
                        type(value) in ALWAYS_CHECK or
                        attr in [PROV_TYPE, PROV_LOCATION, PROV_VALUE]) and \
                        _ns_xsi("type") not in subelem.attrib and \
                        not six.text_type(value).startswith("voprov:") and \
                        not (attr in PROV_ATTRIBUTE_QNAMES and v) and \
                        attr not in [PROV_ATTR_TIME, PROV_LABEL]:
                    xsd_type = None
                    if isinstance(value, bool):
                        xsd_type = XSD_BOOLEAN
                        v = v.lower()
                    elif isinstance(value, six.string_types):
                        xsd_type = XSD_STRING
                    elif isinstance(value, float):
                        xsd_type = XSD_DOUBLE
                    elif isinstance(value, six.integer_types):
                        xsd_type = XSD_INT
                    elif isinstance(value, datetime.datetime):
                        # Exception of the exception, while technically
                        # still correct, do not write XSD dateTime type for
                        # attributes in the PROV namespaces as the type is
                        # already declared in the XSD and PROV XML also does
                        # not specify it in the docs.
                        if attr.namespace.prefix != "prov" \
                                or "time" not in attr.localpart.lower():
                            xsd_type = XSD_DATETIME
                    elif isinstance(value, prov.identifier.Identifier):
                        xsd_type = XSD_ANYURI

                    if xsd_type is not None:
                        subelem.attrib[_ns_xsi("type")] = \
                            six.text_type(xsd_type)

                if attr in PROV_ATTRIBUTE_QNAMES and v:
                    subelem.attrib[_ns_prov("ref")] = v
                else:
                    subelem.text = v
        return xml_bundle_root

    def _derive_record_label(self, rec_type, attributes):
        """
        Helper function trying to derive the record label taking care of
        subtypes and what not. It will also remove the type declaration for
        the attributes if it was used to specialize the type.

        :param rec_type: The type of records.
        :param attributes: The attributes of the record.
        """
        rec_label = FULL_NAMES_MAP[rec_type]

        for key, value in list(attributes):
            if key != VOPROV_TYPE:
                continue
            if isinstance(value, prov.model.Literal):
                value = value.value
            if value in PROV_BASE_CLS and PROV_BASE_CLS[value] != value:
                attributes.remove((key, value))
                rec_label = FULL_NAMES_MAP[value]
                break
        return rec_label


def _ns(ns, tag):
    return "{%s}%s" % (ns, tag)


def _ns_prov(tag):
    return _ns(DEFAULT_NAMESPACES['voprov'].uri, tag)


def _ns_xsi(tag):
    return _ns(DEFAULT_NAMESPACES['xsi'].uri, tag)


def _ns_xml(tag):
    NS_XML = "http://www.w3.org/XML/1998/namespace"
    return _ns(NS_XML, tag)
