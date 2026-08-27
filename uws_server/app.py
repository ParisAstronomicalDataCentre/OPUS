#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
WSGI/ASGI script for UWS server
"""

import os
import sys
import asgiref.wsgi

from uws_server import uws_server

curdir = os.path.dirname(__file__)
sys.path.append(curdir)

# Change working directory so relative paths (and template lookup) work again
os.chdir(curdir)

# WSGI app for e.g. Apache and mod_wsgi
# Do NOT use bottle.run() with mod_wsgi
application = uws_server.app

# ASGI wrapper for uvicorn
asgi_app = asgiref.wsgi.WsgiToAsgi(application)
