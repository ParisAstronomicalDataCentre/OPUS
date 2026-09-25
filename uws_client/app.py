#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
WSGI/ASGI script for UWS client
"""

import os
import sys

from a2wsgi import WSGIMiddleware

from uws_client import uws_client

curdir = os.path.dirname(__file__)
sys.path.append(curdir)

# Change working directory so relative paths (and template lookup) work again
os.chdir(curdir)

# WSGI app for e.g. Apache and mod_wsgi
application = uws_client.app

# ASGI wrapper for uvicorn: the requests are handled by a pool of threads
asgi_app = WSGIMiddleware(application, workers=uws_client.settings.WSGI_THREADS)
