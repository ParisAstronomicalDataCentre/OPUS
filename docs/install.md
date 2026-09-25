
# Installation

OPUS can be installed in three ways:

* **locally with `uv` and `just`** (recommended): the server and the client run with uvicorn, optionally behind
  nginx;
* **with Docker**: uvicorn and nginx in a container, with a PostgreSQL database in another container;
* **with Apache and mod_wsgi**, as in previous versions.

To upgrade an existing installation, see [Upgrade to v0.6](upgrade.md).


## Get the code from the git repository

The web application code can be placed in any directory, e.g. `OPUS_DIR=/opt/opus`. To create the directory, clone
the git repository, then check out the last version:

    $ git clone https://github.com/ParisAstronomicalDataCentre/OPUS.git opus
    $ cd opus
    $ git checkout v0.6

Alternatively, the repository is also available at https://gitlab.obspm.fr/mservillat/OPUS.git.


## Local installation with uv and just

OPUS has been tested on MacOS, Debian/Ubuntu and CentOS, with Python 3.10 and 3.11.

### Requirements

* [uv](https://docs.astral.sh/uv/) to manage the Python environment and dependencies,
* [just](https://just.systems/) to run the commands defined in the `justfile` (`just --list` shows them),
* `git`, `curl` (used by the jobs to report their phase to the server) and `graphviz` (provenance graphs),
* `nginx`, only to run OPUS behind nginx.

They can be installed e.g. with `brew`, `apt-get`... depending on the system.

### Python environment

In the OPUS directory, create the virtual environment `.venv` and install the dependencies:

    $ just install          # uv sync --no-dev (or just install-dev, with the development tools)

### Configuration

The settings of the server and the client have default values in the code (package `opus_config`). The local
configuration is done in a `.env` file in the OPUS directory, with variables prefixed with `OPUS_`. A template is
provided (`.env.dist`), and a `.env` file with random values for the secrets can be generated from it, then edited:

    $ just env > .env
    $ chmod 600 .env

This file contains confidential tokens and passwords, and any specific configuration of OPUS (URLs, Storage,
SLURM...). It should be readable only by the user running OPUS, and never be added to git. The template is self
descriptive for basic features, for more advanced features see [Configuration](settings.md).

OPUS stores its logs, job files and database in a dedicated directory, declared in `.env` as `OPUS_VAR_PATH`
(`local_var` in the OPUS directory by default, or e.g. `/var/opt/opus`). This directory has to be writable by the
user running OPUS. It is created at the first start.

The unit tests may be run to check the main features of the UWS server and client:

    $ just test
    $ just coverage         # with the coverage of the code (or just coverage html: report in htmlcov/)

### Run with the development servers

The server and the client can be run directly with uvicorn, in two different shell sessions:

    $ just server           # UWS server on http://localhost:8082
    $ just client           # client on http://localhost:8080

With the default settings (`OPUS_BASE_URL=http://localhost:8082` and `OPUS_UWS_CLIENT_ENDPOINT=http://localhost:8080`),
the client is then available at http://localhost:8080.

### Run behind nginx

nginx gives access to the server and the client on the same port, under `/opus_server` and `/opus_client`. The URLs
have to be set accordingly in `.env`, e.g.:

    OPUS_BASE_URL=http://localhost/opus_server
    OPUS_UWS_CLIENT_ENDPOINT=http://localhost/opus_client

Then generate the nginx configuration (`nginx/nginx.conf`, from the settings), and start the server, the client and
nginx:

    $ just nginx_conf
    $ just start
    $ just stop             # to stop them

The client is then available at http://localhost/opus_client/. nginx runs as the local user, with its logs in
`$OPUS_VAR_PATH/logs` and its temporary files in `$OPUS_VAR_PATH/nginx`. It listens on port 80: this is allowed for
a local user on MacOS, but on Linux the ports below 1024 are reserved to root (see e.g. the setting
`net.ipv4.ip_unprivileged_port_start`, or change the port in `generate_nginx_config.py`).

`OPUS_BASE_URL` has to be reachable from the machine running the jobs, as the jobs use it to report their phase to
the server.


## Installation with Docker

OPUS can be run in a container (uvicorn + nginx) with a PostgreSQL database. Templates are provided for the image and
the services, they should be copied and modified, and the settings of the container are generated in `.env.docker`
(with random values for the secrets):

    $ cp Dockerfile.dist Dockerfile
    $ cp docker-compose.dist.yml docker-compose.yml
    $ just env .env.docker.dist > .env.docker
    $ chmod 600 .env.docker

The settings in `.env.docker` are given to the container as environment variables (`env_file` in
`docker-compose.yml`), they are not part of the image. `OPUS_BASE_URL` has to be reachable from inside the container,
as jobs use it to report their phase to the server. Then build and start the services:

    $ docker compose up --build -d

The OPUS client is then available at http://localhost/opus_client/. The data (logs, jobs, results) is stored in the
`opus_data` volume, and the database in the `db_data` volume.

The ports of PostgreSQL (5432) and Adminer (8081) are exposed for development, and the database password is `opus`:
for a deployment on a server, remove those ports and change the password in `docker-compose.yml`
(`POSTGRES_PASSWORD`) and in `.env.docker` (`OPUS_PGSQL_PASSWORD`).


## Installation with Apache and mod_wsgi

OPUS can also be run by the Apache 2 web server with the WSGI module (mod_wsgi). The Python environment and the
configuration are prepared as for a local installation (see above: `just install`, then the `.env` file). The
URLs in `.env` are those given by Apache, e.g.:

    OPUS_BASE_URL=https://example.com/opus_server
    OPUS_UWS_CLIENT_ENDPOINT=https://example.com/opus_client

The `.env` file has to be readable by the web server user (e.g. `www-data`, `apache`, `_www`...), and
`OPUS_VAR_PATH` writable by this user.

### WSGI module

The WSGI module should be installed in the Python environment of OPUS, and a `wsgi.conf` file generated to setup the
Apache web server (it loads the module and sets the Python environment):

    $ uv pip install mod_wsgi
    $ uv run mod_wsgi-express module-config > wsgi.conf

Note that `uv sync` (or `just install`) removes the packages that are not dependencies of OPUS, such as mod_wsgi:
use `uv sync --no-dev --inexact` to keep it.

### Web server configuration

The server and the client are run with the scripts `uws_server/wsgi.py` and `uws_client/wsgi.py`. For convenience,
the following links can be created:

    $ cd $OPUS_DIR
    $ ln -sf uws_server/wsgi.py wsgi_server.py
    $ ln -sf uws_client/wsgi.py wsgi_client.py

Apache should be setup by providing the necessary .conf files in the APACHE_CONF directory (e.g. for CentOS this
directory should be `APACHE_CONF=/etc/httpd/conf.d/`; for Debian/Ubuntu, the files should be placed in
`/etc/apache2/sites-available/` with a link from `/etc/apache2/sites-enabled/`, for MacOS the file can be copied
to `/etc/apache2/other/`).

First copy the WSGI module configuration (as root):

    # cp wsgi.conf $APACHE_CONF

Then create a `opus.conf` file to define the virtual host for the OPUS server and client (in `$APACHE_CONF` for
example, or inside `/etc/apache2/extra/httpd-vhosts.conf` for MacOS). A template is given in
`apache/apache_opus.dist.conf`, the paths have to be adapted (`/opt/opus` for the OPUS directory, `/var/opt/opus`
for `OPUS_VAR_PATH`):

    <VirtualHost *:80>
        ServerName example.com
        ServerAdmin  a@b.com
        DocumentRoot /opt/opus
        ErrorLog "/var/opt/opus/logs/apache_error.log"
        CustomLog "/var/opt/opus/logs/apache_access.log" combined
        WSGIApplicationGroup %{GLOBAL}
        WSGIDaemonProcess opus_client display-name=%{GROUP} processes=1 threads=5
        WSGIScriptAlias /opus_client "/opt/opus/wsgi_client.py" process-group=opus_client
        WSGIDaemonProcess opus_server display-name=%{GROUP} processes=1 threads=5
        WSGIScriptAlias /opus_server "/opt/opus/wsgi_server.py" process-group=opus_server
        Alias /static "/opt/opus/uws_client/static"
        WSGIPassAuthorization On
        <Directory "/opt/opus">
            AllowOverride None
            Require all granted
        </Directory>
    </VirtualHost>

After this configuration, the server must be restarted, and logs checked:

    # apachectl restart


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
