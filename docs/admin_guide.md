
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
| Logs               | Last lines of the log files of the server, nginx and the client                   |


### Logs

The log viewer shows the last lines (100 to 5000) of a log file, from `$OPUS_VAR_PATH/logs`:

* server: `server.log` (INFO level), `server_debug.log` (DEBUG level) and `debug.log` (other modules),
* nginx: `nginx_access.log` and `nginx_error.log` (with `just start` or Docker, see `generate_nginx_config.py`),
* client: `client.log` (INFO level) and `client_debug.log` (DEBUG level).

The lines can be filtered (text contained in the line, case insensitive), and are colored by level (warnings and
errors, or HTTP status 4xx and 5xx in the nginx access log). With **Auto refresh**, the log is reloaded every
10 seconds. The selected file is kept in the URL of the page (e.g. `/admin/logs?file=nginx_error`).

The log files of the server and nginx are read through the server (route `/log`, for the admin only, also usable by
scripts with the admin credentials: `curl -u $ADMIN_NAME:$ADMIN_TOKEN "<server>/log?FILE=server_debug&LINES=500"`),
so they are available when the server and the client run on different hosts.


### Client Preferences

The connection of the client to the UWS server can be modified without restarting the client: the URL of the
server (`UWS_SERVER_URL`), its UWS endpoint (`UWS_SERVER_ENDPOINT`) and the authentication method (`UWS_AUTH`). The
default value of each setting (from `.env`) is shown below the field.

The values that differ from the settings are stored in `$OPUS_VAR_PATH/config/uws_client_config.yaml`, and have
priority over `.env`. To go back to the settings of `.env`, set the default values again, or remove this file.

### Client Accounts

This page lists the accounts of the client, and allows to create, edit or delete them: email, password, active
status, token, and roles. The role `admin` gives access to the administration pages, the role `user` is given to
the other accounts, and `oidc` to the accounts created from an Identity Provider. These roles of the client are
different from the roles of the users on the server (see **Server Accounts**).

Users can also create their own account on the registration page of the client (**Register**, next to **Local
login** in the menu), if it is enabled with `OPUS_SECURITY_REGISTERABLE=true` in `.env` (disabled by default). Users can also
sign in with an external account if Identity Providers are configured (`OPUS_OIDC_IDPS`, OpenID Connect): their
account in the client is then created at the first login. The account is identified by the email given by the Identity Provider
(or by its `sub` identifier if no email is given). The login is refused if the Identity Provider indicates that the
email is not verified (`email_verified`), and a local account (created without OIDC) can only be used if the email
is verified.

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


OpenID Connect
--------------

Users can sign in to the client with an Identity Provider (OpenID Connect, e.g. INDIGO-IAM), and the server can
accept the access tokens of these users. The Identity Providers are defined in `.env` (`OPUS_OIDC_IDPS`), and read by
the client and the server, e.g. for INDIGO-IAM (the JSON value may span several lines between single quotes):

    OPUS_OIDC_IDPS='[
        {
            "title": "INDIGO-IAM",
            "description": "Sign in with INDIGO-IAM",
            "url_logo": "",
            "url": "https://<iam-server>/.well-known/openid-configuration",
            "client_id": "<client id>",
            "client_secret": "<client secret>",
            "scope": "openid email profile offline_access",
            "audience": "<audience>"
        }
    ]'

The scope `offline_access` gives a refresh token to the client, to renew the access tokens of the users.

The client and its redirect URL (`<client>/accounts/oidc/callback`) have to be registered on the Identity Provider,
which gives the `client_id` and `client_secret` (only used by the client).

### Access tokens on the server

The server accepts requests with the access token of a user (`Authorization: Bearer <access token>`) **and** the
OPUS token of the account (header `X-Opus-Token`): the access token proves the identity of the user, the OPUS token
selects the account (name + token). The HTTP Basic authentication is still accepted, e.g. for scripts.

The access token must be a JWT signed by one of the Identity Providers of `OPUS_OIDC_IDPS` (as INDIGO-IAM tokens).
The server checks it with the keys of the Identity Provider (found with its discovery URL): signature, issuer,
expiration, and **audience** if `audience` is defined for the Identity Provider (recommended: the token is then
only accepted if it was requested for OPUS). The name of the user is the email given by the userinfo endpoint of the
Identity Provider (INDIGO-IAM does not include it in the access tokens by default), or the `sub` identifier.

### Client

To send the access tokens of the users to the server, set `OPUS_UWS_AUTH=OIDC` in `.env` (or **UWS_AUTH** in the
**Client Preferences** page). The client then keeps the tokens of the users signed in with an Identity Provider
(in its database, never sent to the browser), refreshes them when they expire, and sends them to the server with the
OPUS token of the user. It removes them when the user signs out. For the other users (local accounts), or if the
token cannot be refreshed, the client uses the HTTP Basic authentication (`OPUS_UWS_AUTH=Basic`, the default).

### Logs

The access tokens are never written in the logs. The requests with an access token can be followed in:

* `server_debug.log`: `OIDC access token accepted for <name> (iss=<issuer>, sub=<sub>)` for each request with a
  valid access token,
* `server.log` and `server_debug.log`: `OIDC access token refused: <reason>` (warning) for an invalid token,
* `client_debug.log`: the authentication used for each request sent to the server, e.g.
  `GET http://.../uws/<jobname> (200, OIDC)` or `(200, Basic)`.

### Logout

When a user signed in with an Identity Provider signs out, the client revokes its tokens on the Identity Provider (if
it has a `revocation_endpoint`, as INDIGO-IAM), and removes them. The user is always signed out of the client, even
if the Identity Provider cannot be reached.

The session of the user on the Identity Provider is also ended:

* if the Identity Provider supports the standard RP-initiated logout (`end_session_endpoint` in its discovery
  document): the user is redirected to it, then back to the home page of the client, whose URL has to be registered
  as a post-logout redirect URI on the Identity Provider (e.g. `http://localhost/opus_client/` for `just start`);
* else, only if `logout_url` is defined for the Identity Provider in `OPUS_OIDC_IDPS` (not by default): the user is
  redirected to this URL, and stays on the Identity Provider (e.g. `https://<iam-server>/logout` for INDIGO-IAM,
  which does not support the RP-initiated logout yet).

Ending the session on the Identity Provider signs the user out of all the applications using it (single sign-on): if
it is not ended, the next login with the Identity Provider does not ask for the password again.


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

The server provides a maintenance task that archives the jobs whose destruction date is passed (phase `ARCHIVED`,
see `USE_ARCHIVED_PHASE`: their results are deleted, their description is kept, and they are no longer shown in the
job lists; the deletion of the results is not implemented yet, they are currently kept), and, with the SLURM
manager, updates the phase of the jobs still running on the work cluster.
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
| `python -m uws_server.migrate_users`       | Migrate the `users` and `entities` tables of a database created by a previous version (see [Upgrade to v0.6](upgrade.md)) |
| `python -m uws_client.rotate_tokens`       | Replace the predictable tokens of previous versions (see [Upgrade to v0.6](upgrade.md)) |

They make a dry run by default, and apply the changes with `--apply` (backup the databases before).
