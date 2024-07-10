
# Installation

## Get the code from the git repository

The web application code can be placed in any directory, e.g. `OPUS_DIR=/opt/OPUS`. To create the `OPUS` directory, clone the git repository:

    $ git clone https://github.com/ParisAstronomicalDataCentre/OPUS.git

Alternatively :

    $ git clone https://gitlab.obspm.fr/mservillat/OPUS.git



## Setting the environment

OPUS has been tested on MacOS, Debian/Ubuntu and CentOS. The web application generally uses Apache 2 and the WSGI module connected to a Python 3 environment.

The following packages may be needed if not already installed in the environment (e.g. using `yum`, `apt-get`, `pkg`, `brew`... depending on the distribution):

    $ <install_command> git bzip2 graphviz httpd-devel libpq-dev perl-Digest-SHA

The Python 3 environment (last version tested: python-3.11.8) can be installed with Anaconda (check the [https://conda.io/docs/user-guide/install/index.html](Miniconda3
installation page)). A virtual environment should be created, e.g. with the following commands:

    $ cd $OPUS_DIR
    $ conda create --name opus python==3.11
    $ conda activate opus
    $ pip install -r requirements.txt

Check also the other requirement files:
* `requirements.txt`: requirements for `pip`
* `requirements_freeze.txt`: requirements for `pip` with last version tested
* `requirements_conda.txt`: requirements for `conda` packages


## Prepare local configuration

Several files in the distribution contain initial settings for the server and the client. The local configuration is done by creating a `settings_local.py` file in the OPUS directory. Settings in this file will overwrite the initial settings. A template is provided and should be copied and modified:

    $ cp settings_local.dist.py settings_local.py

This file contains confidential tokens and defaults passwords, and any specific configuration of OPUS (Storage, SLURM...). The template is self descriptive for basic features. For more advanced features, see the dedicated page for Settings.

OPUS stores its logs, job files and database in a dedicated directory, e.g. `OPUS_VAR=/var/opt/opus`. It is declared in `settings_local.py` as `VAR_PATH`. This directory has to be writable by the server and client, so writable by the user running the applications (either the web server user or a local user).

The unit tests may be run to check the main features of the UWS server:

    $ make test


## Local execution with developments servers

It is possible to run the application from the command line with a development server. To test the application, run the following commands in two different shell sessions:

    $ python run_server.py
    Bottle v0.12.25 server starting up (using WSGIRefServer())...
    Listening on http://localhost:8082/
    Hit Ctrl-C to quit.

    $ python run_client.py
     * Serving Flask app 'uws_client.uws_client'
     * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
     * Running on http://localhost:8080
    Press CTRL+C to quit

From a web browser, the OPUS server or client URL should redirect to the OPUS client home page.


## Preparing the WSGI web server

The WSGI module should then be installed within this virtual environment, and a `wsgi.conf` file generated to setup the
 Apache web server:

    $ pip install mod_wsgi
    $ mod_wsgi-express module-config
    $ mod_wsgi-express module-config > wsgi.conf


## Web server configuration

The `uws_server/uws_server.py` file  can be directly run to test the application on
`localhost:8080`.

With Apache 2 and mod_wsgi, use the script `uws_server/wsgi.py` or create a similar script. In the
same way, the client can be run directly (`uws_client/uws_client.py`) or using the script `uws_client/wsgi.py`. For
convenience, the following links can be created:

    $ cd $OPUS_DIR
    $ ln -sf uws_server/wsgi.py wsgi_server.py
    $ ln -sf uws_client/wsgi.py wsgi_client.py

Apache should be setup by providing the necessary .conf files in the APACHE_CONF directory (e.g. for CentOS this
directory should be `APACHE_CONF=/etc/httpd/conf.d/`; for Debian/Ubuntu, the files should be placed in
`/etc/apache2/sites-available/` with a link from `/etc/apache2/sites-enabled/`, for MacOS the file can be copied
to `/etc/apache2/other/`).

First copy the WSG module configuration (as root):

    # cp wsgi.conf $APACHE_CONF

Then create a `opus.conf` file to define virtual hosts for the OPUS server and client (in `$APACHE_CONF` for example,
or inside `/etc/apache2/extra/httpd-vhosts.conf` for MacOS), the content would then be:

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


After this configuration, the server must be restarted, and logs checked:

    # apachectl restart
    # apachectl


## SLURM Work Cluster configuration

In order to send and manage jobs on a SLURM Work Cluster, the UWS Server must be specifically configured.

A dedicated account must be defined on the SLURM Work Cluster and declared in the UWS Server settings. This account
must be accessible through SSH by copying the UWS Server SSH public key in the `.ssh/authorized_keys` file on the
SLURM Work Cluster dedicated account home directory.

The oncompletion plugin can be added to SLURM to send a signal on specific SLURM events (TIMEOUT, PREEMPTED, ...).
This is done by adding in the dedicated script (e.g. `/usr/local/sbin/slurm_job_completion.sh`) a curl command for
the SLURM account (`<UID>`) that sends a signal to the `<BASE_URL>` as follow:

    if [[ "$UID" -eq <UID> ]]; then
        curl -k --max-time 10 -d jobid="$JOBID" -d phase="$JOBSTATE" <BASE_URL>/handler/job_event
    fi
