
User guide
==========


Administration from the UWS Client
----------------------------------

### Login as the administrator of OPUS

The default login name is ‘opus-admin‘ and the default password for the UWS Client is set locally in 
`uws_client/settings_local.py`. This password should be changed after install.
  
In order to be the administrator of an OPUS UWS Server, the client account must have the name and token defines for 
the UWS Server in the variables ADMIN_NAME and ADMIN_TOKEN. The token can be set through the Profile page in the UWS 
Client (upper right menu).

From this menu, the administrator can access the following pages:

* **Client Preferences**: view and modify the connection to the UWS Server (UWS_SERVER_URL and UWS_AUTH)

* **Client Accounts**: view and modify the client accounts (name and password for the client, token to connect to the 
server)

* **Server Accounts**: view and modify the server accounts (name and token on the server), import accounts to the client

* **Server Jobs**: list available job definitions on the server


Job definition editor
---------------------

### Create a new job definition



### Validate a job definition


Create and manage jobs from the UWS Client
------------------------------------------

### Run a job

### Check the status

### Edit the job properties, parameters and results

### Check the job details


Create and manage jobs using Python uws-client
----------------------------------------------

