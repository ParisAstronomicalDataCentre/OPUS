import sys, os

sys.path.append('/var/www/bottle/uws_server/')

# Change working directory so relative paths (and template lookup) work again
os.chdir(os.path.dirname(__file__))

import bottle
import uws_server

# Do NOT use bottle.run() with mod_wsgi
application = uws_server.app

