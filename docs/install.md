Server Installation
===================
Get the code from the git repository
------------------------------------
    $ git clone https://github.com/mservillat/opus.git

Initialize the package
----------------------
Move to the main directory and install the required python packages:

    $ pip install -r pip-requirements.txt
    
Intitialize the data tree structure and make it writable by the web server. The 
variable WWWUSER can be used to set the username used by the web server. it is 
set to `www` by default:

    $ make init
    $ make init WWWUSER=wwwuser
    
Run unit tests to check tha main features of the UWS server:

    $ make test

Configure your web server
-------------------------
The `uws_server.py` file  can be directly run to test the application on
`localhost:8080`.

With Apache 2 and mod_wsgi, use the script `uws_server/wsgi.py`.
The following configuration file (e.g. `uws_server.conf`) should be placed in
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

-----

Client only installation
========================
The `uws_client.py` file can be directly run to test the application on
`localhost:8080`.

With Apache 2 and mod_wsgi, use the script `uws_client/wsgi.py` as explained above
to install the client as is. However, one may adapt the web pages to integrate 
the JavaScript web client to a specific web application.
