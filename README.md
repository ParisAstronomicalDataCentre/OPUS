
Overview
========
**OPUS** (**O**bservatoire de **P**aris **U**WS **S**ystem) is a job control 
system developed using the micro-framework bottle.py. The Universal Worker System 
pattern v1.0 (UWS) as defined by the International Virtual Observatory Alliance 
(IVOA) is implemented as a REST service to control job execution on a work cluster.

Documentation
=============
[![Documentation Status](https://readthedocs.org/projects/uws-server/badge/?version=latest)](http://uws-server.readthedocs.org/en/latest/?badge=latest)

The documentation located in `docs/` can be accessed at http://uws-server.readthedocs.org/ 

Installation
============

Get the code from the git repository
------------------------------------
    $ git clone https://github.com/mservillat/opus.git

Initialize the package
----------------------
    $ cd OPUS
    $ pip install -r pip-requirements.txt
    $ make init
    $ make test

Configure your web server
-------------------------
For example with Apache 2 and mod_wsgi using the script `uws_server/wsgi.py`, 
the following configuration file (e.g. uws_server.conf) should be placed in 
`/etc/apache2/sites-available/` with a link from `/etc/apache2/sites-enabled/`.

    <VirtualHost *:80>
    
        ServerName example.com
        ServerAdmin  a@b.com
        DocumentRoot /path_to_uws_server
        ErrorLog "/var/log/error.log"
        CustomLog "/var/log/access.log" combined
        Header set Access-Control-Allow-Origin "*"  
              
        WSGIDaemonProcess uws display-name=%{GROUP} processes=1 threads=5
        WSGIProcessGroup uws
        WSGIScriptAlias / "/path_to_uws_server/uws_server/wsgi.py"
        WSGIPassAuthorization On
        
        <Directory "/path_to_uws_server">
        AllowOverride None
        Require all granted
        </Directory>
        
    </VirtualHost>