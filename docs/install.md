Installation
============
Get the code from the git repository
------------------------------------
The web application code can be placed in any directory, e.g. `OPUS_DIR=/opt/OPUS`. To create the `OPUS` directory, 
simply clone the git repository:

    $ git clone https://github.com/ParisAstronomicalDataCentre/OPUS.git

Setting the environment
-----------------------

OPUS has been successfully installed on MacOS, Debian/Ubuntu and CentOS. The web application generally uses Apache 2 
and the WSGI module connected to a Python 3.6 environment.

The following packages may be needed if not already installed in the environment: git, bzip2, graphviz, httpd-devel, 
perl-Digest-SHA (e.g. for CentOS, using yum install`).

The Python 3 environment used in all cases installed with the Anaconda distribution (check the [https://conda.io/docs/user-guide/install/index.html](Miniconda3 
installation page)). A virtual environment should be created, e.g. with the following commands:

    $ cd $OPUS_DIR
    $ conda create --name wsgi36 python==3.6
    $ source activate wsgi36
    $ pip install -r pip-requirements.txt
    
The WSGI module should then be installed within this virtual environment, and a `wsgi.conf` file generated to setup the
 Apache web server:
    
    $ pip install mod_wsgi
    $ mod_wsgi-express module-config
    $ mod_wsgi-express module-config > wsgi.conf

OPUS then requires a directory to store its logs, files and database, e.g. `OPUS_VAR=/var/www/opus`. This directory 
must be writable from the web application, i.e. by the user Apache is running as (e.g. www, www-data or apache).
The `$OPUS_VAR/logs` directory must also be created and writable for this user, if the logs are written in this 
directory (see Apache configuration proposed below).
    
The unit tests may be run to check the main features of the UWS server:

    $ make test

Configure the web server
------------------------

The `uws_server/uws_server.py` file  can be directly run to test the application on
`localhost:8080`. With Apache 2 and mod_wsgi, use the script `uws_server/wsgi.py` or create a similar script. In the 
same way, the client can be run directly (`uws_client/uws_client.py`) or using the script `uws_client/wsgi.py`. For 
convenience, the following links can be created:

    $ cd $OPUS_DIR
    $ ln -sf uws_server/wsgi.py wsgi_server.py
    $ ln -sf uws_client/wsgi.py wsgi_client.py

Apache should be setup by providing the necessary .conf files in the APACHE_CONF directory (e.g. for CentOS this 
directory should be `APACHE_CONF=/etc/httpd/conf.d/`; for Debian/Ubuntu, the files should be placed in 
`/etc/apache2/sites-available/` with a link from `/etc/apache2/sites-enabled/`). 

First copy the WSG module configuration (as root):

    # cp wsgi.conf $APACHE_CONF

Then create a `opus.conf` file to define virtual hosts for the OPUS server and client, the content would then be:

    <VirtualHost *:80>
        ServerName example.com
        ServerAdmin  a@b.com
        DocumentRoot /opt/OPUS
        ErrorLog "/var/www/opus/logs/apache_error.log"
        CustomLog "/var/www/opus/logs/apache_access.log" combined
        Header set Access-Control-Allow-Origin "*"
        WSGIDaemonProcess opus_client display-name=%{GROUP} processes=1 threads=5
        WSGIScriptAlias /opus_client "/opt/OPUS/wsgi_client.py" process-group=opus_client
        WSGIDaemonProcess opus_server display-name=%{GROUP} processes=1 threads=5
        WSGIScriptAlias /opus_server "/opt/OPUS/wsgi_server.py" process-group=opus_server
        Alias /static "/opt/OPUS/uws_client/static"
        WSGIPassAuthorization On
        <Directory "/opt/OPUS">
            AllowOverride None
            Require all granted
        </Directory>
    </VirtualHost>

