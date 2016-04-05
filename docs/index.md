
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

The **UWS client** is based on the JavaScript library `uwsLib.js` that can be
used independently to send requests to the server. The core of the client is the
`uws_manager.js` file that is used to create requests, parse responses, and then
display job lists and job properties in web pages.A set of HTML pages use those
scripts and are accessed through bottle.py functions. A separate web page allows
the user to create and modify job descriptions. Note that the UWS client uses the
JavaScript frameworks BootStrap3 and jQuery.


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
The `uws_server.py` file  can be directly run to test the application on
`localhost:8080`.

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
The `uws_client.py` file can be directly run to test the application on
`localhost:8080`.

With Apache 2 and mod_wsgi, use the script `uws_client/wsgi.py` to install the
client as is. However, one may adapt the web pages to integrate the JavaScript
web client to a specific web application.


Settings
========

DEBUG
    If True, the full trace of an error is shown on the error web page.
    If False, the error webpage is simply "Internal Server Error".

APP_PATH
    Path to the application files. Autoset to the package directory (parent
    of the uws_server/settings.py file).

BASE_URL
    Base URL of the server hosting the applciation.

MERGE_CLIENT
    If true the UWS client bottle.py application is merged to the UWS server
    application.

LOG_FILE
    name of the log file

JOB_SERVERS
    dictionnary of IP adresses allowed to access the job_event/ endpoint of
    the UWS server. Only the job servers can send events to change the status
    of a job.

STORAGE
    Storage class to be used by the UWS server. Additional settings are relative
    to the Storage class selected.

MANAGER
    Manager class to be used by the UWS server. Additional settings are relative
    to the Manager class selected.


User guide
==========



Developer guide
===============
How to create new classes
-------------------------
Manager and Storage classes are empty parent classes with the minimum functions
required:

    class Manager(object):
        """
        Manage job execution on cluster. This class defines required functions executed
        by the UWS server: start(), abort(), delete(), get_status(), get_info(),
        get_results() and cp_script().
        """

        def start(self, job):
            """Start job on cluster
            :return: jobid_cluster, jobid on cluster
            """
            return 0

        def abort(self, job):
            """Abort/Cancel job on cluster"""
            pass

        def delete(self, job):
            """Delete job on cluster"""
            pass

        def get_status(self, job):
            """Get job status (phase) from cluster
            :return: job status (phase)
            """
            return job.phase

        def get_info(self, job):
            """Get job info from cluster
            :return: dictionary with job info
            """
            return {'phase': job.phase}

        def get_results(self, job):
            """Get job results from cluster"""
            pass

        def cp_script(self, jobname):
            """Copy job script to cluster"""
            pass


    class Storage(object):
        """
        Manage job information storage. This class defines required functions executed
        by the UWS server save(), read(), delete()
        """

        def save(self, job, save_attributes=True, save_parameters=True, save_results=True):
            """Save job information to storage (attributes, parameters and results)"""
            pass

        def read(self, job, get_attributes=True, get_parameters=True, get_results=True,
                 from_jobid_cluster=False):
            """Read job information from storage"""
            pass

        def delete(self, job):
            """Delete job information from storage"""
            pass

        def get_list(self, joblist):
            """Delete job information from storage"""
            pass


Child classes should be develop to fit one's need. Currently only the SQLiteStorage
and SLURMManager classes are implemented and can be used as examples.
