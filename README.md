
UWS Server
==========
Job controller server and client developed using the micro-framework 
bottle.py. The standard pattern Universal Worker System v1.0 (UWS) 
to manage job execution as defined by the International Virtual 
Observatory Alliance (IVOA) is implemented as a REST service.

Installation
============

Get the code from the git repository
------------------------------------
    $ git clone https://github.com/mservillat/uws-server.git

Initialize the package
----------------------
    $ pip install -r requirements.txt
    $ make init
    $ make test

Configure your web server
-------------------------
For example with Apache 2 and mod_wsgi using the script `uws_server/wsgi.py`, 
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