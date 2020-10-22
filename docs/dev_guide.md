Developer guide
===============
Contribute to the code development
----------------------------------
The development follows the 
[Github workflow](https://guides.github.com/introduction/flow/) to add new features. 
First fork the repository then propose a pull request!

How to create new classes
-------------------------
Manager and Storage classes are empty parent classes with the minimum functions
required. Child classes should thus be develop to fit one's need. Currently only the 
`SQLiteStorage` and `SLURMManager` classes are implemented and can be used as examples.

```python
class Manager(object):
    """
    Manage job execution on cluster. This class defines required functions executed
    by the UWS server: start(), abort(), delete(), get_status(), get_info(),
    get_jobdata() and cp_script().
    """

    def start(self, job):
        """Start job on cluster
        :return: jobid_cluster, jobid on cluster
        """
        return 0

    def abort(self, job):
        """Abort/Cancel job on cluster"""
        pass

    def delete(self, job):
        """Delete job on cluster"""
        pass

    def get_status(self, job):
        """Get job status (phase) from cluster
        :return: job status (phase)
        """
        return job.phase

    def get_info(self, job):
        """Get job info from cluster
        :return: dictionary with job info
        """
        return {'phase': job.phase}

    def get_jobdata(self, job):
        """Get job results from cluster"""
        pass

    def cp_script(self, jobname):
        """Copy job script to cluster"""
        pass
```

```python
class Storage(object):
    """
    Manage job information storage. This class defines required functions executed
    by the UWS server save(), read(), delete()
    """

    def save(self, job, save_attributes=True, save_parameters=True, save_results=True):
        """Save job information to storage (attributes, parameters and results)"""
        pass

    def read(self, job, get_attributes=True, get_parameters=True, get_jobdata=True,
             from_jobid_cluster=False):
        """Read job information from storage"""
        pass

    def delete(self, job):
        """Delete job information from storage"""
        pass

    def get_list(self, joblist):
        """Delete job information from storage"""
        pass
```
