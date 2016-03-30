import os
import sys

curdir = os.path.dirname(__file__)
sys.path.append(curdir)

# Change working directory so relative paths (and template lookup) work again
os.chdir(curdir)

import bottle
from uws_server import uws_server

# Do NOT use bottle.run() with mod_wsgi
application = uws_server.app

