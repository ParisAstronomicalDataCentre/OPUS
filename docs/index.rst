
Overview
========
The **UWS Server** is a job control system developed using the micro-framework
bottle.py. The Universal Worker System pattern v1.0 (UWS) as defined
by the International Virtual Observatory Alliance (IVOA) is implemented
as a REST service to manage job execution on a work cluster.

More information on the UWS pattern recommendation can be found here:

http://www.ivoa.net/documents/UWS/20101010/

The **UWS server** is composed of:
* a REST interface following the bottle.py framework and the UWS recommendation,
* a set of classes to define, create and manage UWS jobs and job lists
* Storage classes to store job properties in a database (currently only the
SQLiteStorage class is available),
* Manager classes to communicate with a work cluster (currently only the
SLURMManager class is available),
* Job description language (JDL) functions to read and write descriptions
(currently the WADL standard is used).

The **UWS client** is based on the JavaScript library `uwsLib.js that can be
used independently to send requests to the server. The core of the client is the
`uws_manager.js` file that is used to create requests, parse responses, and then
display job lists and job properties in web pages. A set of HTML pages use those
scripts and are accessed through bottle.py functions. A separate web page allows
the user to create and modify job descriptions.


Server Installation
===================

Get the code from the git repository
------------------------------------
    $ git clone https://github.com/mservillat/uws_server.git

Initialize the package
----------------------
    $ pip install -r requirements.txt
    $ make init
    $ make test

Configure your web server
-------------------------

The file uws_server.py can be directly run to test the application on localhost:8080

With Apache 2 and mod_wsgi, use the script `uws_server/wsgi.py`.
the following configuration file (e.g. uws_server.conf) should be placed in
`/etc/apache2/sites-available/` with a link to `/etc/apache2/sites-enabled/`.

    <VirtualHost *:80>

        ServerName example.com
        ServerAdmin  a@b.com
        DocumentRoot /path_to_uws_server
        ErrorLog "/var/log/error_ssl.log"
        CustomLog "/var/log/access_ssl.log" combined
        Header set Access-Control-Allow-Origin "*"

        WSGIDaemonProcess uws display-name=%{GROUP} processes=1 threads=5
        WSGIProcessGroup uws
        WSGIScriptAlias / "/path_to_uws_server/uws_server/wsgi.py"

        <Directory "/path_to_uws_server">
        AllowOverride None
        Require all granted
        </Directory>

    </VirtualHost>


Client only installation
========================



Settings
========




User guide
==========



Developer guide
===============

How to create new classes
-------------------------


