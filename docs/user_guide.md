
User guide
==========


Administration from the UWS Client
----------------------------------

### Login as the administrator of OPUS

The default login name is ‘opus-admin‘ and the default password for the UWS Client is set locally in
`settings_local.py`. This password should be secured and changed after install.

In order to be the administrator of an OPUS UWS Server, the client account ‘opus-admin‘ must have the name and token defines for
the UWS Server in the variables ADMIN_NAME and ADMIN_TOKEN. The token can be changed in the UWS Client through the Profile page (top-right menu).

From the top-right menu, the administrator can access the following specific pages:

* **Client Preferences**: view and modify the connection to the UWS Server (UWS_SERVER_URL and UWS_AUTH)

* **Client Accounts**: view and modify the client accounts (name and password for the client, token to connect to the
server)

* **Server Accounts**: view and modify the server accounts (name and token on the server), import accounts to the client

* **Server Jobs**: list available job definitions on the server


Job definition editor
---------------------

### Create a new job definition

The Job Definition Editor provides a form to describe a job with a job name, some metadata, an then a list of parameters, expected input data and expected generated results.

Example jobs are provided in `test_jobs/`. Those files can be imported from the Job Definition Editor.

Once the job definition form is imported, click the **Submit JDL form** button.
This will create a temporary job with the prefix `tmp/` that must be validated by the administrator of OPUS.
The administrator of OPUS should receive a notification by email.

### Validate a job definition



Create and manage jobs from the UWS Client
------------------------------------------

### Run a job

### Check the status

### Edit the job properties, parameters and results

### Check the job details



Create and manage jobs using Python uws-client
----------------------------------------------
