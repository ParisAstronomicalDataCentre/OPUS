
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
For example using Apache 2 and mod_wsgi, with the script `uws_server/wsgi.py`.

    <VirtualHost *:80>
    
        ServerName voparis-uws-test.obspm.fr
        ServerAdmin  a@b.com
        DocumentRoot /share/web/uws_server
        ErrorLog "/var/log/error_ssl.log"
        CustomLog "/var/log/access_ssl.log" combined
        Header set Access-Control-Allow-Origin "*"  
              
        WSGIDaemonProcess uws display-name=%{GROUP} processes=1 threads=5
        WSGIProcessGroup uws
        WSGIScriptAlias / "/share/web/uws_server/uws_server/wsgi.py"

        <Directory "/share/web/uws_server">
        AllowOverride None
        Require all granted
        </Directory>
        
    </VirtualHost>