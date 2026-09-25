
Upgrading to v0.6
=================

This page explains how to upgrade an OPUS installation from a previous version to v0.6. It applies to
installations at the tag `v0.5`, or at any later commit before `v0.6` (the last one being `dde7ae9`).
To know the version of an installation, run in the OPUS directory:

    $ git describe --tags
    v0.5-229-gdde7ae9

The output gives the last tag, the number of commits since this tag, and the commit hash (after `g`). The hash of
the running version is also given in the source of the home page of the client (element `git_version`).

The upgrade has to be done on each installation. Some steps are **required to fix security issues**, see below.


Security issues fixed
---------------------

| Issue | Impact | Fix in v0.6 | Action on existing installations |
| ---   | :---   | :---        | :---                             |
| The key signing the session cookies of the client (`app.secret_key`) was written in the code, so publicly known | Anyone could forge the content of a session cookie (e.g. the state of an OpenID Connect login). The identity of the logged-in user is not affected, as it relies on a random identifier. | The key is the required setting `OPUS_SECRET_KEY` | Generate a random `OPUS_SECRET_KEY` in `.env` (step 3). All users are logged out once. |
| The token of a new client user was predictable: it could be computed by others. | The token authenticates the user on the UWS server: access to the jobs and results of other users. | Tokens are random (setting `TOKEN_GEN`) | Replace the existing predictable tokens (step 5) |
| On the server, a request with an existing user name and any token replaced the token of this user in the `users` table | With `CHECK_PERMISSIONS=true`, anyone could get the job permissions (roles) of any user, who then lost them. Access to existing jobs was not affected (owner token of each job). | A user is identified by name + token: another token is another account, without roles | Migrate the `users` table (step 4) |
| A validation error of the settings could show all the values read, including secrets | Secrets in logs or tracebacks | Values are hidden in validation errors | None |


Main changes
------------

* **Settings are read from a `.env` file** (or environment variables prefixed with `OPUS_`), see
  [Configuration](settings.md). `settings_local.py` is no longer read: **OPUS does not start** if it is present without a `.env` file,
  to avoid running with the default settings instead of the local ones.
* `OPUS_SECRET_KEY` and `OPUS_SECURITY_PASSWORD_SALT` are **required**. The salt used until now was `test`: it has to
  be kept, or all the existing passwords of the client users are invalidated (`generate_env.py --from` does it).
* **Docker**: the settings are given at runtime with `env_file: .env.docker` in `docker-compose.yml`, they are no
  longer copied in the image (`settings_docker.py` is no longer used). `nginx.conf` is generated at the start of
  the container. See the templates `Dockerfile.dist`, `docker-compose.dist.yml` and `.env.docker.dist`.
* On the server, a user is identified by **name + token**: the same name (e.g. an email) can have several accounts,
  one per token (e.g. one per client), each with its own roles and jobs. Changing the token of a user on the profile
  page of the client means using another account on the server.
* The access rules are **restrictive by default**: `ALLOW_ANONYMOUS=false`, `CHECK_PERMISSIONS=true` and
  `CHECK_OWNER=true` (previously `true`, `false` and `false`). The values defined in `settings_local.py` are kept by
  the conversion to `.env` (step 3): check them in `.env`, the new defaults apply to the values that were not
  defined. See the [Admin guide](admin_guide.md) for the roles of the users.
* The registration page of the client (`/accounts/register`), previously always enabled, is **disabled by
  default**: set `OPUS_SECURITY_REGISTERABLE=true` in `.env` to keep it.
* New dependency: `pydantic-settings` (installed by `uv sync`).


Upgrade procedure
-----------------

The commands are run in the OPUS directory (`$OPUS_DIR`), in the Python environment of OPUS: with `uv`, prefix
the `python` commands with `uv run` (e.g. `uv run python generate_env.py`). For Docker, see the next section.

**1. Backup** the data directory (`VAR_PATH`, e.g. `/var/opt/opus`), in particular the client database
(`db/flask_login.db`) and the server database (`db/job_database.db` for SQLite, or a dump for PostgreSQL), as well
as `settings_local.py`.

**2. Get the new version** and install the dependencies (stop OPUS before):

    $ git fetch --tags
    $ git checkout v0.6
    $ uv sync --no-dev          # with uv, or in another environment: pip install -e .

**3. Create the `.env` file** from `settings_local.py` (the values are converted, a random `OPUS_SECRET_KEY` is added,
and the salt used until now is kept):

    $ python generate_env.py --from settings_local.py > .env
    $ chmod 600 .env

Check the content of `.env`, in particular the ignored values listed at the end of the file, and the tokens:
replace `TBD` or empty values by random values, e.g. generated with:

    $ python -c "import secrets; print(secrets.token_urlsafe(32))"

Note that `OPUS_ADMIN_TOKEN` must not be changed if scripts use it. Then remove `settings_local.py`
(it is saved in the backup):

    $ rm settings_local.py

For a new installation (no `settings_local.py`), generate `.env` from the template instead:
`python generate_env.py > .env`.

**4. Migrate the `users` table** of the server database (the server logs a warning at start until it is done):

    $ python -m uws_server.migrate_users            # dry run: show the current schema
    $ python -m uws_server.migrate_users --apply

**5. Replace the predictable tokens** of the client users (after step 4):

    $ python -m uws_client.rotate_tokens            # dry run: list the users to update
    $ python -m uws_client.rotate_tokens --apply

With `--all`, all the tokens are replaced (except the admin token): this is recommended if the installation was
moved or copied from another place.

**6. Start OPUS and inform the users**: they have to log in again, and those who use their token outside of the
web client (scripts, command line) have to get the new one from their profile page.


Upgrade procedure with Docker
-----------------------------

**1. Backup** the volumes (`opus_data` and `db_data`), e.g. with a dump of the database:

    $ docker compose exec -T db pg_dump -U opus opus > opus_backup.sql

**2. Get the new version** (`git fetch --tags && git checkout v0.6`), and update `Dockerfile` and `docker-compose.yml`
from the templates `Dockerfile.dist` and `docker-compose.dist.yml` (`env_file`, pinned `postgres` image...).

**3. Create `.env.docker`** from `settings_docker.py`, then check it as in step 3 above:

    $ uv run python generate_env.py --from settings_docker.py > .env.docker
    $ chmod 600 .env.docker

**4. Build and start** the containers:

    $ docker compose up --build -d

**5. Migrate the `users` table and replace the predictable tokens**, in the container:

    $ docker compose exec opus-app uv run --no-sync python -m uws_server.migrate_users --apply
    $ docker compose exec opus-app uv run --no-sync python -m uws_client.rotate_tokens --apply

(run them first without `--apply` to check what will be done). Then remove `settings_docker.py`, and inform the
users (step 6 above).


Rollback
--------

Steps 4 and 5 modify the databases: to go back to the previous version, restore the backups of the databases and of
`settings_local.py`, then check out the previous version (e.g. `git checkout dde7ae9`).
