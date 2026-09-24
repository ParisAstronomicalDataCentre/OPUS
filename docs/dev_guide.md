Developer guide
===============
Contribute to the code development
----------------------------------
The development follows the 
[Github workflow](https://guides.github.com/introduction/flow/) to add new features. 
First fork the repository then propose a pull request!

How to create new classes
-------------------------
The job execution and the job storage are done by classes chosen in the settings
(see [Configuration](settings.md)):

| Setting        | Class used                                      | Implemented classes                           |
| ---            | :---                                            | :---                                          |
| `MANAGER`      | `<MANAGER>Manager` in `uws_server/managers.py`  | `LocalManager` (default), `SLURMManager`      |
| `STORAGE`      | `<STORAGE>JobStorage` in `uws_server/storage.py`| `SQLAlchemyJobStorage` (default)              |
| `JDL`          | `<JDL>` in `uws_server/uws_jdl.py`              | `VOTFile` (default), `WADLFile`, `JSONFile`   |

* `LocalManager` runs the jobs on the UWS server itself, with Bash commands.
* `SLURMManager` runs the jobs on a SLURM work cluster, through SSH (see the SLURM section of the
  [Installation](install.md) page).
* `SQLAlchemyJobStorage` stores the jobs, users and entities in a relational database through SQLAlchemy:
  SQLite or PostgreSQL, depending on the setting `STORAGE_TYPE`.

`Manager`, `JobStorage`, `UserStorage` and `EntityStorage` are parent classes that define the functions required by
the UWS server. A new class should inherit from them and implement those functions, e.g. `MyManager(Manager)`
selected with `OPUS_MANAGER=My`. `LocalManager`, `SLURMManager` and `SQLAlchemyJobStorage` can be used as examples.

```python
class Manager:
    """
    Manage job execution. This class defines required functions executed
    by the UWS server: start(), abort(), delete(), get_status(), get_info(),
    get_jobdata() and cp_script().
    """

    def start(self, job):
        """Start job
        :return: process_id, jobid on work cluster
        """
        return 0

    def abort(self, job):
        """Abort/Cancel job"""
        pass

    def delete(self, job):
        """Delete job"""
        pass

    def get_status(self, job):
        """Get job status (phase)
        :return: job status (phase)
        """
        return job.phase

    def get_info(self, job):
        """Get job info
        :return: dictionary with job info
        """
        return {"phase": job.phase}

    def get_jobdata(self, job):
        """Get job results"""
        pass

    def cp_script(self, jobname):
        """Copy job script"""
        pass
```

`LocalManager` only implements `start()`, `abort()` and `delete()`: the other functions are not needed as the jobs
run on the UWS server directly. The `Manager` class also provides helper functions to prepare the batch script of a
job, which reports the phase of the job to the server (`<BASE_URL>/handler/job_event`).

```python
class JobStorage:
    """
    Manage job information storage. This class defines required functions executed
    by the UWS server save(), read(), delete()
    """

    def save(self, job, save_attributes=True, save_parameters=True, save_results=True):
        """Save job information to storage (attributes, parameters and results)"""
        pass

    def read(self, job, get_attributes=True, get_parameters=True, get_results=True,
             from_process_id=False):
        """Read job information from storage"""
        pass

    def delete(self, job):
        """Delete job information from storage"""
        pass

    def get_list(self, joblist, phase=None, where_owner=True):
        """Get job list from storage"""
        pass
```

`UserStorage` defines the functions to manage the users of the server: `get_users()`, `add_user()`,
`remove_user()`, `update_user()`, `add_role()`, `remove_role()`, `has_role()` and `has_access()`. A user is
identified by its name and its token: the same name can have several accounts, one per token, each with its own
roles (access to jobs).

`EntityStorage` defines the functions to manage the entities (input and output files of the jobs, for the
provenance): `register_entity()`, `remove_entity()`, `get_entity()` and `search_entity()`.
