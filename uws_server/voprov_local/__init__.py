# -*- coding: utf-8 -*-
# Copy of the voprov package under MIT License

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from prov import Error

__author__ = 'Jean-Francois Sornay'
__email__ = 'jeanfrancois.sornay@gmail.com'
__version__ = '2.0.1'

__all__ = ["Error", "models", "read"]


def read(source, format=None):
    """
    Convenience function returning a VOProvDocument instance.

    It does a lazy format detection by simply using try/except for all known
    formats. The deserializers should fail fairly early when data of the
    wrong type is passed to them thus the try/except is likely cheap. One
    could of course also do some more advanced format auto-detection but I am
    not sure that is necessary.

    The downside is that no proper error messages will be produced, use the
    format parameter to get the actual traceback.
    """
    # Lazy imports to not globber the namespace.
    from voprov.models.model import VOProvDocument

    from voprov.serializers import Registry
    Registry.load_serializers()
    serializers = Registry.serializers.keys()

    if format:
        return VOProvDocument.deserialize(source=source, format=format.lower())

    for format in serializers:
        try:
            return VOProvDocument.deserialize(source=source, format=format)
        except:
            pass
    else:
        raise TypeError("Could not read from the source. To get a proper "
                        "error message, specify the format with the 'format' "
                        "parameter.")
