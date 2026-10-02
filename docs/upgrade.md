
Upgrading to v1.0
=================

This page explains how to upgrade an OPUS installation from a previous version to v1.0. It applies to
installations at the tag `v0.5`, or at any later commit before `v1.0`.
To know the version of an installation, run in the OPUS directory:

    $ git describe --tags
    v0.5-229-gdde7ae9

The output gives the last tag, the number of commits since this tag, and the commit hash (after `g`): note it
before the upgrade, it is the version to go back to (see Rollback). The hash of the running version is also given
in the source of the home page of the client (element `git_version`).

The upgrade has to be done on each installation. Some steps are **required to fix security issues**, see below.


Security issues fixed
---------------------

| Issue | Impact | Fix in v1.0 | Action on existing installations |
| ---   | :---   | :---        | :---                             |
| The key signing the session cookies of the client (`app.secret_key`) was written in the code, so publicly known | Anyone could forge the content of a session cookie (e.g. the state of an OpenID Connect login). The identity of the logged-in user is not affected, as it relies on a random identifier. | The key is the required setting `OPUS_SECRET_KEY` | Generate a random `OPUS_SECRET_KEY` in `.env` (step 3). All users are logged out once. |
| The token of a new client user was predictable: it could be computed by others. | The token authenticates the user on the UWS server: access to the jobs and results of other users. | Tokens are random (setting `TOKEN_GEN`) | Replace the existing predictable tokens (step 5) |
| On the server, a request with an existing user name and any token replaced the token of this user in the `users` table | With `CHECK_PERMISSIONS=true`, anyone could get the job permissions (roles) of any user, who then lost them. Access to existing jobs was not affected (owner token of each job). | A user is identified by name + token: another token is another account, without roles | Migrate the `users` table (step 4) |
| With `CHECK_OWNER=true`, a result file (`/store`) could be downloaded by any account with the name of its owner, whatever its token | Access to the results of another account with the same name (e.g. the same email on another client) | The owner of a file is identified by name + token, as for jobs | None: the owner token of the existing files is set at the start of the server, from their jobs (or with step 4). The files without known job are still checked by owner name only |
| At the login of a user with OpenID Connect, the tokens given by the Identity Provider were written in the debug log of the client, as well as the token of the user in other log lines | Access and refresh tokens readable in `client_debug.log` | Tokens are no longer written in the logs | Remove the lines containing `token = ` from `$OPUS_VAR_PATH/logs/client_debug.log` (or the whole file), and if possible revoke the tokens at the Identity Provider |
| A user signing in with OpenID Connect was linked to the local account with the same email, even if the Identity Provider did not verify the email | Access to a local account with an Identity Provider allowing unverified emails | The email has to be verified to use a local account, and the login is refused if the email is not verified | None |
| At the logout of a user signed in with OpenID Connect, its tokens were not revoked on the Identity Provider | The tokens stayed valid until their expiration | The tokens are revoked at logout (if the Identity Provider has a `revocation_endpoint`) | None |
| A validation error of the settings could show all the values read, including secrets | Secrets in logs or tracebacks | Values are hidden in validation errors | None |
| The IPs of `JOB_SERVERS` (allowed to report job events) and `TRUSTED_CLIENTS` were accepted if they were contained in the IP of a request | Other addresses were accepted: e.g. `::1` accepted any IPv6 address containing `::1`, and `127.0.0.1` accepted `127.0.0.10` | An IP is matched exactly, a set of IPs is written with `*` (e.g. `192.168.1.*`), and the values are checked at start | Check `OPUS_JOB_SERVERS` and `OPUS_TRUSTED_CLIENTS` in `.env`: write a truncated IP (e.g. `"127.0.0."`) as `"127.0.0.*"` (still read, with a warning). **The server does not start** with a key that is neither an IP nor a set of IPs |


Main changes
------------

* **Settings are read from a `.env` file** (or environment variables prefixed with `OPUS_`), see
  [Configuration](settings.md). `settings_local.py` is no longer read: **OPUS does not start** if it is present without a `.env` file,
  to avoid running with the default settings instead of the local ones.
* `OPUS_SECRET_KEY` and `OPUS_SECURITY_PASSWORD_SALT` are **required**. The salt was before hard-coded in 
  `uws_client/settings.py`: it has to be kept, or all the existing passwords of the client users are invalidated 
  (`generate_env.py --from` does it, otherwise, set it in the `.env` file).
* **Docker**: the settings are given at runtime with `env_file: .env.docker` in `docker-compose.yml`, they are no
  longer copied in the image (`settings_docker.py` is no longer used). `nginx.conf` is generated at the start of
  the container. The database service takes its user, database and password from `.env.docker` too
  (`OPUS_PGSQL_*`): the password is no longer written in `docker-compose.yml`, and **has to be set in
  `.env.docker`** (see the Docker procedure below). See the templates `Dockerfile.dist`,
  `docker-compose.dist.yml` and `.env.docker.dist`.
* On the server, a user is identified by **name + token**: the same name (e.g. an email) can have several accounts,
  one per token (e.g. one per client), each with its own roles and jobs. Changing the token of a user on the profile
  page of the client means using another account on the server.
* The access rules are **restrictive by default**: `ALLOW_ANONYMOUS=false`, `CHECK_PERMISSIONS=true` and
  `CHECK_OWNER=true` (previously `true`, `false` and `false`). The values defined in `settings_local.py` are kept by
  the conversion to `.env` (step 3): check them in `.env`, the new defaults apply to the values that were not
  defined. See the [Admin guide](admin_guide.md) for the roles of the users.
* The registration page of the client (`/accounts/register`), previously always enabled, is **disabled by
  default**: set `OPUS_SECURITY_REGISTERABLE=true` in `.env` to keep it.
* **OpenID Connect on the server** (optional, disabled by default): the server can accept the access tokens of the
  users signed in with an Identity Provider, sent by the client with `OPUS_UWS_AUTH=OIDC` or by scripts, with their
  OPUS token. `OPUS_OIDC_IDPS` is now read by the server too, and the client keeps the tokens in a new table
  (`oidc_token`, created at start). At logout, the tokens are revoked, and the session on the Identity Provider can
  be ended (`logout_url`). See the [Admin guide](admin_guide.md).
* When the server refuses a request of a visitor who is not signed in (e.g. `ALLOW_ANONYMOUS=false`), the client
  redirects to the login page.
* The maintenance of the jobs (archiving after their destruction date) is not automatic: it should be scheduled
  (step 7), e.g. with the new `just maintenance` recipe.
* **Archiving a job now deletes its result files** (and uploaded files): its description, parameters, logs and
  provenance are kept, a result is still listed but its file is no longer available. The maintenance also removes
  the result files of the jobs archived before the upgrade, and **deletes** the jobs after their destruction date
  that cannot be archived (not completed, aborted or in error). The new **Maintenance** page of the client (admin)
  shows what would be done (dry run) before applying it, see the [Admin guide](admin_guide.md).
* `EXECUTION_DURATION_MAX` was not used: it now limits the execution duration of the jobs (from the job
  definition, or set by a user). Its default is `0` (no limit, previously `3600`): a value kept from
  `settings_local.py` is now applied.
* Changes of the UWS interface of the server, for the scripts and other clients using it: the job list is given
  **newest first**, and `LAST=n` gives the `n` most recent jobs (previously oldest first, and the `n` oldest); the
  creation of a job with a missing or invalid input, and an invalid `EXECUTIONDURATION` value, are refused with
  a `400` (previously `500`); an event for a job already completed, aborted or archived is ignored with a `409`.
* **Web client**: Bootstrap 5 (previously 3), jQuery 3.7 and CodeMirror 5.65, in `uws_client/static/vendor/`.
  Templates, styles or scripts modified locally have to be adapted. New pages for the administrator: Maintenance,
  Job Definitions (validation, history of the versions, deleted definitions), Logs. The list of all the jobs is at
  `/jobs/_all_` (previously `/jobs/all`, still accepted if no job is named `all`). The client can also show the
  jobs of an external UWS service, e.g. a TAP server (see the [Admin guide](admin_guide.md)).
* New settings: `OPUS_BATCH_SHELL` (shell of the job scripts, `/bin/bash -l` by default), and `OPUS_UWS_AUTH=None`
  (no credentials sent by the client, for an external service). The template `.env.dist` gives the default and the
  possible values of the settings.
* Removed files: `run_server.py` and `run_client.py` (use `just server` and `just client`), `Makefile` (use the
  `justfile`, e.g. `just test`), `Dockerfile_apache` and `Dockerfile_apache.dist`. `start.sh` is renamed
  `docker-start.sh` (entry point of the Docker image). `just start` no longer reloads the code when it changes: use
  `just restart`.
* The server and the client handle the requests **in parallel** (pool of `OPUS_WSGI_THREADS` threads, 10 by
  default), with uvicorn: previously, one request at a time was handled, e.g. a job list waiting for a phase
  change (`WAIT`) blocked the other requests.
* The provenance of chained jobs is complete in both directions: a job using a result of another job now records
  it (`DIRECTION=FORWARD` in `/provsap`, for the jobs created after the upgrade), and the internal provenance
  written by a job (`internal_provenance.json`) is included.
* Dependencies: `pydantic-settings` and `a2wsgi` (replaces `asgiref`) are new, `prov` is limited to the versions
  below 3; they are installed by `uv sync`.
* The log file `debug.log` of the server (other modules) is no longer written: it stayed empty (the messages of the
  `prov` library are now in `server_debug.log`). It can be removed from `$OPUS_VAR_PATH/logs`.


Upgrade procedure
-----------------

The commands are run in the OPUS directory (`$OPUS_DIR`), in the Python environment of OPUS: with `uv`, prefix
the `python` commands with `uv run` (e.g. `uv run python generate_env.py`). For Docker, see the next section.

**1. Backup** the data directory (`VAR_PATH`, e.g. `/var/opt/opus`), in particular the client database
(`db/flask_login.db`) and the server database (`db/job_database.db` for SQLite, or a dump for PostgreSQL), as well
as `settings_local.py`.

**2. Get the new version** and install the dependencies (stop OPUS before):

    $ git fetch --tags
    $ git checkout v1.0
    $ uv sync --no-dev          # with uv, or in another environment: pip install -e .

**3. Create the `.env` file** from `settings_local.py` (the values are converted, a random `OPUS_SECRET_KEY` is added,
and the salt used until now is kept):

    $ python generate_env.py --from settings_local.py > .env
    $ chmod 600 .env

Check the content of `.env`, in particular the ignored values listed at the end of the file, the IPs of
`OPUS_JOB_SERVERS` and `OPUS_TRUSTED_CLIENTS` (see the security issues above), and the tokens: replace `TBD` or
empty values by random values, e.g. generated with:

    $ python -c "import secrets; print(secrets.token_urlsafe(32))"

Then remove `settings_local.py` (it is saved in the backup):

    $ rm settings_local.py

For a new installation (no `settings_local.py`), generate `.env` from the template instead:
`python generate_env.py > .env`.

**4. Migrate the `users` table** of the server database (the server logs a warning at start until it is done).
This also adds the owner token to the `entities` table (result files), which is otherwise done at the start of
the server:

    $ python -m uws_server.migrate_users            # dry run: show the current schema
    $ python -m uws_server.migrate_users --apply

**5. Replace the predictable tokens** of the client users (after step 4):

    $ python -m uws_client.rotate_tokens            # dry run: list the users to update
    $ python -m uws_client.rotate_tokens --apply

With `--all`, all the tokens are replaced (except the admin token): this is recommended if the installation was
moved or copied from another place.

**6. Start OPUS and inform the users**: they have to log in again, and those who use their token outside of the
web client (scripts, command line) have to get the new one from their profile page.

**7. Schedule the maintenance of the jobs** (recommended), e.g. daily with `cron` (see the [Admin guide](admin_guide.md)).
It deletes the result files of the archived jobs, and the jobs that cannot be archived: check first what it would
do on the existing jobs, with the Maintenance page of the client (dry run):

    0 3 * * * cd /opt/opus && just maintenance >> /var/opt/opus/logs/maintenance.log 2>&1


Upgrade procedure with Docker
-----------------------------

**1. Backup** the volumes (`opus_data` and `db_data`), e.g. with a dump of the database:

    $ docker compose exec -T db pg_dump -U opus opus > opus_backup.sql

**2. Get the new version** (`git fetch --tags && git checkout v1.0`), and update `Dockerfile` and `docker-compose.yml`
from the templates `Dockerfile.dist` and `docker-compose.dist.yml` (`env_file`, pinned `postgres` image,
`docker-start.sh` entry point...).

**3. Create `.env.docker`** from `settings_docker.py`, then check it as in step 3 above:

    $ uv run python generate_env.py --from settings_docker.py > .env.docker
    $ chmod 600 .env.docker

**Warning: set the password of the database in `.env.docker`.** The database service no longer has a password
in `docker-compose.yml`, it reads `OPUS_PGSQL_PASSWORD` from `.env.docker`, and the converted file may not contain
it. Add the line with the password of the existing `db_data` volume, i.e. the value of `POSTGRES_PASSWORD` in the
previous `docker-compose.yml` (`opus` if it was not changed):

    OPUS_PGSQL_PASSWORD=<current password of the database>

Without it, OPUS uses its default password, and a new database (no `db_data` volume yet) cannot be created.
To change the password of an existing database, see [Installation](install.md).

**4. Build and start** the containers:

    $ docker compose up --build -d

**5. Migrate the `users` table and replace the predictable tokens**, in the container:

    $ docker compose exec opus-app uv run --no-sync python -m uws_server.migrate_users --apply
    $ docker compose exec opus-app uv run --no-sync python -m uws_client.rotate_tokens --apply

(run them first without `--apply` to check what will be done). Then remove `settings_docker.py`, and inform the
users (step 6 above).

**6. Schedule the maintenance of the jobs** (recommended), e.g. daily with `cron` on the host:

    0 3 * * * cd /opt/opus && docker compose exec -T opus-app curl -sS http://localhost:8082/handler/maintenance/__all__


Rollback
--------

Steps 4 and 5 modify the databases: to go back to the previous version, restore the backups of the databases and of
`settings_local.py`, then check out the previous version (the commit noted before the upgrade, e.g.
`git checkout dde7ae9`). The result files deleted by the maintenance (archived or deleted jobs) are only in the
backup of the data directory.
