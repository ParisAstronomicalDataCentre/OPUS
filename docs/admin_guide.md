
Admin guide
===========

This page describes the administration of OPUS: the administrator account, the configuration of the client, the
management of the users and of the job definitions, and the maintenance of the server. The installation and the
settings are described in [Installation](install.md) and [Configuration](settings.md), the use of the client in the
[User guide](user_guide.md).


Administrator account
---------------------

The administrator account of the client is created at the first start of the client, with:

* the login name `ADMIN_NAME` (default: `opus-admin`),
* the password `OPUS_ADMIN_DEFAULT_PW` defined in `.env`: it should be changed after the installation
  (**Change password** in the top-right menu),
* the token `OPUS_ADMIN_TOKEN` defined in `.env`.

On the server, the administrator is the user with the name `ADMIN_NAME` and the token `ADMIN_TOKEN` (the same
settings are read by the server and the client). This user has access to all the jobs and to the administration
functions of the server. The token of the administrator account in the client must thus stay equal to
`OPUS_ADMIN_TOKEN` (see the **Show profile** page).

A test account (`testuser`, password `OPUS_TESTUSER_DEFAULT_PW`) is also created at the first start.


Administration pages
--------------------

When signed in as an administrator (role `admin` in the client), the top-right menu gives access to:

| Page               | Content                                                                           |
| ---                | :---                                                                              |
| Client Preferences | Connection of the client to the UWS server                                        |
| Client Accounts    | Accounts of the client (email, password, token, roles)                            |
| Server Accounts    | Accounts of the server (name, token, permissions)                                 |
| Server Jobs        | Job definitions available on the server                                           |
| Server log         | Last lines of the log of the server                                               |
| Client log         | Last lines of the log of the client                                               |


### Client Preferences

The connection of the client to the UWS server can be modified without restarting the client: the URL of the
server (`UWS_SERVER_URL`), its UWS endpoint (`UWS_SERVER_ENDPOINT`) and the authentication method (`UWS_AUTH`). The
default value of each setting (from `.env`) is shown below the field.

The values that differ from the settings are stored in `$OPUS_VAR_PATH/config/uws_client_config.yaml`, and have
priority over `.env`. To go back to the settings of `.env`, set the default values again, or remove this file.

### Client Accounts

This page lists the accounts of the client, and allows to create, edit or delete them: email, password, active
status, token, and roles. The role `admin` gives access to the administration pages. The other roles are given to
the accounts when they are created, but are not checked by the client: `user`, `oidc` (account created from an
Identity Provider), `job_definition` and `job_list`. The **Roles** page (Flask-Admin) lists and edits the roles.

Users can also create their own account on the registration page of the client (`/accounts/register`). This page is
not linked from the menu, but it is enabled (`SECURITY_REGISTERABLE` in `uws_client/settings.py`). Users can also
sign in with an external account if Identity Providers are configured (`OPUS_OIDC_IDPS`, OpenID Connect): their
account in the client is then created at the first login.

### Server Accounts

This page lists the accounts of the server, i.e. the users that sent requests to the server. On the server, a user
is identified by its name **and** its token: the same name can have several accounts, one per token (e.g. one per
client), each with its own jobs and permissions. For each account, the page allows to:

* set its **roles**: the job names that this user can run (or `all`), used when `OPUS_CHECK_PERMISSIONS=true`,
* change its **token**,
* **delete** it,
* **import** it in the client: a client account is created with the same name and token, then its password has to
  be set in the form that is displayed.

A new account can also be added to the server, with its roles.

### Server Jobs

This page lists the job definitions validated on the server, with their version, contact, type and subtype. They
can be exported (JDL file), or deleted.


Access rules
------------

The access to the server is defined by the following settings in `.env` (see [Configuration](settings.md)):

| Setting                  | Default | Description                                                              |
| ---                      | :---    | :---                                                                     |
| `OPUS_ALLOW_ANONYMOUS`   | `false` | Allow requests without authentication (user `anonymous`)                  |
| `OPUS_CHECK_PERMISSIONS` | `true`  | Check that the user has the role to create/edit the jobs of a given name  |
| `OPUS_CHECK_OWNER`       | `true`  | Only the owner of a job (name + token) can access it and its results      |
| `OPUS_NJOBS_MAX`         | `0`     | Maximum number of active jobs per user (`0` for no limit)                 |
| `OPUS_APP_TOKENS`        | `{}`    | Tokens of applications, giving access to some jobs                        |

The default values are the most restrictive: users have to be signed in, can only run the jobs allowed by their
roles, and only access their own jobs. In particular, a new user has no role: they cannot run any job until the
administrator gives them roles in the **Server Accounts** page (their account on the server is created at their
first login in the client). The administrator has access to all the jobs.

For a private or test installation, the access can be opened in `.env`, e.g. `OPUS_ALLOW_ANONYMOUS=true` and
`OPUS_CHECK_PERMISSIONS=false`.


Job definitions
---------------

### Validate a job definition

A new job definition, or a modification of an existing one, is prepared in the Job Definition Editor (see the
[User guide](user_guide.md)). Submitting the form creates a temporary definition `tmp/<name>`, and the user can then
request its validation: the administrator receives an email (to `OPUS_ADMIN_EMAIL`, through the mail server defined
by `OPUS_MAIL_SERVER` and `OPUS_MAIL_PORT`), with the link to the definition.

To validate it, open the Job Definition Editor, load the definition `tmp/<name>`, check it (parameters, script...)
and click **Validate** (this button is only shown to the administrator). The definition and its script are then
copied from `tmp/<name>` to `<name>`, and the job is available to the users. If a previous version of the job
existed, it is kept in the `saved/` directories:

* `$OPUS_VAR_PATH/jdl/votable/saved/<name>_v<version>_<date>_vot.xml` for the definition,
* `$OPUS_VAR_PATH/jdl/scripts/saved/<name>_v<version>_<date>.sh` for the script.

With the SLURM manager, the script is also copied to the work cluster.

Example job definitions are provided in the `test_jobs/` directory, and can be imported in the Job Definition
Editor (**Import JDL**).

### Remove a job definition

A job definition can be deleted from the **Server Jobs** page.


Maintenance
-----------

### Logs

The logs are written in `$OPUS_VAR_PATH/logs` (`server.log`, `client.log`, and more detailed `*_debug.log` files).
The last lines of the server and client logs can also be seen in the administration pages.

### Maintenance of the jobs

The server provides a maintenance task that updates the phase of the jobs still running, and archives the jobs
whose destruction date is passed (their results are deleted, their description is kept, see `USE_ARCHIVED_PHASE`).
The server only accepts it from its own host. It is not run automatically: it should be run regularly, e.g. once a
day with `cron`.

For a local installation (development servers or behind nginx), run in the OPUS directory:

    $ just maintenance                      # all the jobs
    $ just maintenance <jobname>            # only the jobs with this name

e.g. in the crontab of the user running OPUS (the path of `just` may have to be given):

    0 3 * * * cd /opt/opus && just maintenance >> /var/opt/opus/logs/maintenance.log 2>&1

With Docker, run it in the container:

    $ docker compose exec opus-app curl -sS http://localhost:8082/handler/maintenance/__all__

With Apache, send the request to the URL of the server from the server host, e.g.:

    $ curl -sS http://localhost/opus_server/handler/maintenance/__all__

### Maintenance commands

The following commands are run in the OPUS directory (with `uv run` for a `uv` environment):

| Command                                    | Description                                                   |
| ---                                        | :---                                                          |
| `python generate_env.py > .env`            | Generate a `.env` file with random secrets (see [Installation](install.md)) |
| `python -m uws_server.migrate_users`       | Migrate the `users` table of a database created by a previous version (see [Upgrade to v0.6](upgrade.md)) |
| `python -m uws_client.rotate_tokens`       | Replace the predictable tokens of previous versions (see [Upgrade to v0.6](upgrade.md)) |

They make a dry run by default, and apply the changes with `--apply` (backup the databases before).
