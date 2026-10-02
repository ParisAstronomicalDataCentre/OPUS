
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
| Job Definitions    | Job definitions to validate, validated job definitions and their history          |
| Maintenance        | Check of the jobs (dry run), then changes applied on request (see below)          |
| Logs               | Last lines of the log files of the server, nginx and the client                   |


### Logs

The log viewer shows the last lines (100 to 5000) of a log file, from `$OPUS_VAR_PATH/logs`:

* server: `server.log` (INFO level) and `server_debug.log` (DEBUG level, with the messages of the `prov` library),
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
When an administrator signs in while some values differ from the settings, a warning lists them with their
defaults, until it is closed.

#### Jobs of an external UWS service (e.g. a TAP server)

The client can show the jobs of a UWS service that is not an OPUS server, for example the asynchronous queries of
a TAP server (`<TAP URL>/async`). For `http://voparis-tap-he.obspm.fr/tap/async`, set in the Client Preferences:

| Setting               | Value                           |
| ---                   | :---                            |
| `UWS_SERVER_URL`      | `http://voparis-tap-he.obspm.fr` |
| `UWS_SERVER_ENDPOINT` | `/tap`                          |
| `UWS_AUTH`            | `None`                          |

The client then reads the **capabilities** of the service (`<service URL>/capabilities`): for a TAP service
(`standardID="ivo://ivoa.net/std/TAP"`), the job list is `async`, as fixed by the TAP standard, and its jobs are
listed in the Job List page (`<client>/jobs`). For another service, the name of its job list has to be given in the
URL (`<client>/jobs/<name>`).

Such a server has no job definitions, so a job is shown with its own parameters and results. The job list of the
service may only give the identifier and the phase of the jobs, in any order: the button **Refresh with details**
gets the details of each job (one request per job, a few at a time) to fill its run id and creation time, and
sorts the list by creation time, newest first. The pages for the administration of an OPUS server (accounts, job
definitions, maintenance, server logs) do not apply.

The client has **built-in descriptions** for the standards it knows, in the file
`uws_client/static/js/uws_descriptions.json` (loaded by `uws_descriptions.js`, which describes its format): a TAP
query has the parameters `QUERY`, `LANG`, `RESPONSEFORMAT`, `MAXREC`, `RUNID` and `UPLOAD`, completed with the
capabilities of the service (query languages, output formats, default and limit of the number of rows, uploads
accepted or not, limits of the jobs). With a description, a job can be created with **Create New Job** (the query
is submitted and started) and started; the jobs cannot be aborted, deleted or run again from the client. Without
description, the jobs are **read-only**: the buttons that create or modify a job are disabled. If the capabilities
of the service are not available, the description is found from the name of the job list (`async`).

When the service gives no type or name for the result of a job (e.g. `result` for a TAP query), its type is found
from the format parameter of the job (`RESPONSEFORMAT`, a VOTable by default), and the file is named after the
job (e.g. `async_<jobid>.vot`, or `.csv`). The result is downloaded and previewed through the client, if it is on
the server of the service.

**Set `UWS_AUTH` to `None` for an external service**: with `Basic` or `OIDC`, the name and the OPUS token (or
access token) of the users would be sent to this service.

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

### Job Definitions

This page (previously **Server Jobs**) has three parts:

* **Job definitions to validate**: the job definitions submitted by the users (`tmp/<name>`) that are new, or
  different from the validated version, with the user who submitted them, their date, and whether the validation
  was requested. For each one: **Diff** (differences with the validated version), **Open** (in the Job Definition
  Editor), **Validate**, and **Reject** (the submitted version is removed, with an optional message kept in the
  history).
* **Validated job definitions**, with their version, contact, type and subtype. They can be edited, exported (JDL
  file) or deleted, and their **History** shows:
    * the versions, most recent first: submitted (if any), current, and the previous versions kept in `saved/`
      (dated when they were validated), each one can be compared with the previous or the current version
      (unified diff of the job definition and of the script);
    * the events: submitted (form or import), validation requested, validated, rejected, deleted, restored, with
      the user and the date. The events are recorded in `$OPUS_VAR_PATH/jdl/history/<name>.jsonl` since this
      version of OPUS: the job definitions validated before have their previous versions, but no events.

    A previous version can be **restored**: it becomes the validated version again (the version that was validated,
    if any, is kept in `saved/`, and the restored version stays in the history).
* **Deleted job definitions**: the job definitions found in the history without validated version, invisible to
  the users: deleted (with their last version, which can be **restored**, and their history), or never validated
  (e.g. rejected).


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

To validate it, use the **Job Definitions** page (list of the job definitions to validate, with the differences
with the validated version), or open the Job Definition Editor, load the definition `tmp/<name>`, check it
(parameters, script...) and click **Validate** (this button is only shown to the administrator). The validation
request is recorded in the history even if the email cannot be sent. A validated or rejected job definition is
removed from `tmp/`, as well as a job definition of `tmp/` identical to the validated version (e.g. kept in `tmp/`
by a previous version of OPUS: removed at the start of the server). The definition and its script are then
moved from `tmp/<name>` to `<name>`, and the job is available to the users. If a previous version of the job
existed, it is kept in the `saved/` directories:

* `$OPUS_VAR_PATH/jdl/votable/saved/<name>_v<version>_<date>_vot.xml` for the definition,
* `$OPUS_VAR_PATH/jdl/scripts/saved/<name>_v<version>_<date>.sh` for the script.

With the SLURM manager, the script is also copied to the work cluster.

Example job definitions are provided in the `test_jobs/` directory, and can be imported in the Job Definition
Editor (**Import JDL**).

### Remove a job definition

A job definition can be deleted from the **Job Definitions** page (it is kept in the `saved/` directories, with
`_DELETED` in the name).


Maintenance
-----------

### Logs

The logs are written in `$OPUS_VAR_PATH/logs` (`server.log`, `client.log`, and more detailed `*_debug.log` files).
The last lines of the server and client logs can also be seen in the administration pages.

### Maintenance of the jobs

The server provides a maintenance task for the jobs whose destruction date is passed:

* the jobs COMPLETED, ABORTED or in ERROR are archived (phase `ARCHIVED`, see `USE_ARCHIVED_PHASE`): their results
  files are deleted (result files and uploaded files), their description is kept (attributes, parameters, results,
  logs and provenance: a result is still listed, its file is no longer available), and they are no longer shown in
  the job lists,
* the other jobs (e.g. PENDING, or still EXECUTING), or all the jobs if `USE_ARCHIVED_PHASE=false`, are deleted: the
  job is stopped if it is running, its files (uploads, job data, results) and its entries in the database are
  removed, as when a user deletes a job.

It also removes the result files of the jobs already archived that still have them (e.g. archived by a previous
version of OPUS, which kept the files).

With the SLURM manager, it also updates the phase of the jobs still running on the work cluster.
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

The **Maintenance** page of the client (admin menu) runs the same checks on demand:

* **Check (dry run)** lists the categories in a table (number of jobs, description), nothing is changed: jobs to
  archive, jobs to delete (see above), phase to update from the job manager, inconsistent dates, errors, archived
  jobs and jobs without issue. No job is listed at first: **Show** on a category lists its jobs in a second
  table below (several categories can be shown), and **Show all** lists the jobs of all the categories.
* The column **Apply** selects the changes to apply: jobs to archive, phases to update, jobs to delete, result
  files to remove for the jobs already archived (all selected by default). For the jobs to archive, the action can be **Archive** (default) or **Delete**: the jobs are then
  deleted with their files instead of being archived (the check is run again to list the change of each job).
* **Apply changes** (after a check, with a confirmation listing the selected changes and the number of jobs)
  applies them, then runs a new check: the page gives what was applied (number of jobs by change) and the
  current state.

The checks cover all the jobs of the database, including the jobs of job definitions that were deleted. The page uses
the route `/maintenance` of the server (admin only): `GET` for a dry run, `POST` to apply, with the optional
parameters `JOBNAME`, `APPLY` (changes to apply, may be repeated: `to_archive`, `to_delete`, `phase`,
`archived_files`, all by default, or `none`) and `ARCHIVE_ACTION` (`archive` by default, or `delete`), and a JSON report. The maintenance
task run by `cron` (`just maintenance`) applies all the changes, and archives the jobs.

### Capabilities and availability of the server

The server describes itself with the IVOA Support Interfaces (VOSI), for the registries and the other clients. Both
pages are public, and give no job name or user information:

* `<server>/capabilities`: the endpoints of the server and the standards they follow:
    * the UWS job lists (`ivo://ivoa.net/std/UWS#rest-1.1`, base URL `<server>/uws`, one list per job definition),
    * the job definitions (`<server>/jdl`) and the provenance of the jobs (`<server>/provsap`, IVOA ProvSAP), with
      identifiers specific to OPUS (`https://opus-job-manager.readthedocs.io/#jdl` and `#provsap`): they have no
      registered IVOA identifier,
    * the two VOSI pages themselves.
* `<server>/availability`: the server is available if its database can be read, with the date of its start.

### Maintenance commands

The following commands are run in the OPUS directory (with `uv run` for a `uv` environment):

| Command                                    | Description                                                   |
| ---                                        | :---                                                          |
| `python generate_env.py > .env`            | Generate a `.env` file with random secrets (see [Installation](install.md)) |
| `python -m uws_server.migrate_users`       | Migrate the `users` and `entities` tables of a database created by a previous version (see [Upgrade to v1.0](upgrade.md)) |
| `python -m uws_client.rotate_tokens`       | Replace the predictable tokens of previous versions (see [Upgrade to v1.0](upgrade.md)) |

They make a dry run by default, and apply the changes with `--apply` (backup the databases before).
