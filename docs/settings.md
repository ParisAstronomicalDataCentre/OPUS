Settings
========

The file `settings.py` contains the following variables that are specific to an 
installation, and should thus be set before running the application:

**DEBUG**:  
    If True, the full trace of an error is shown on the error web page.  
    If False, the error webpage is simply "Internal Server Error".

**APP_PATH**:  
    Path to the application files. Autoset to the package directory (parent
    of the uws_server/settings.py file).

**BASE_URL**:  
    Base URL of the server hosting the applciation.

**MERGE_CLIENT**:  
    If True the UWS client bottle.py application is merged to the UWS server
    application.

**LOG_FILE**:  
    name of the log file.

**JOB_SERVERS**:  
    Dictionnary of IP adresses allowed to access the job_event/ endpoint of
    the UWS server. Only the job servers can send events to change the status
    of a job.

**TRUSTED_CLIENTS**:  
    Dictionnary of IP adresses allowed to access the job manager part of the client.

**JDL**:  
    Class to be used to read job definition files.
    
**STORAGE**:  
    Storage class to be used by the UWS server. Additional settings are relative
    to the Storage class selected.

**MANAGER**:  
    Manager class to be used by the UWS server. Additional settings are relative
    to the Manager class selected.
