# -*- coding: utf-8 -*-
"""
Created on Tue May 11 2015

@author: mservillat
"""

import datetime
import subprocess as sp
from settings import *


# -------------
# Manager class


class Manager(object):
    """Manage job execution on cluster

    This class defines required functions executed by the UWS server:
    start(), abort(), delete() and get_status()
    """

    def start(self, job):
        """Start job on cluster

        Returns:
            jobid_cluster: jobid on cluster
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

        Returns:
            job status (phase)
        """
        return 'UNKNOWN'


class SLURMManager(Manager):
    """Manage interactions with SLURM (e.g. on tycho.obspm.fr)"""

    def __init__(self, host=SLURM_URL, user=SLURM_USER, mail=SLURM_USER_MAIL):
        self.host = host
        self.user = user
        self.mail = mail
        self.ssh_arg = user + '@' + host
        # self.sbatch = sbatch
        self.pbs_path = 'uws_pbs/'
        self.params_path = 'uws_params/'
        self.uws_handler = 'uws_scripts/uws_handler.sh'

    def make_pbs(self, job):
        """Make PBS file content for given job

        Returns:
            PBS as a string
        """
        duration = datetime.timedelta(0, job.execution_duration)
        # duration format is 00:01:00 for 1 min
        duration_str = str(duration).replace(' days', '').replace(' day', '').replace(', ', '-')
        pbs = [
            "#!/bin/sh",
            "### Job name",
            "#SBATCH --job-name=%s_%s" % (job.jobname, job.jobid),
            "### Declare job non-rerunable",
            "#SBATCH --no-requeue",
            "### Output files",
            "#SBATCH --error=uws_logs/%j.err",
            "#SBATCH --output=uws_logs/%j.job",
            "### Mail to user",
            "#SBATCH --mail-user=" + self.mail,
            "#SBATCH --mail-type=ALL",
            "#Time",
            "#SBATCH --time=" + duration_str,
            "#Memory",
            "#SBATCH --mem=200mb",
            "#Define number of processors",
            "#SBATCH --nodes=1 --ntasks-per-node=1",
            "### Queue name (small, long)",
            "### Script execution",
            "/obs/vouws/uws_scripts/ctbin.pl 'voplus.obspm.fr/cta/events.fits' 5",
            #"/home/vouws/uws/%s.pl '%s'" % (job.jobname, job.jobid),
        ]
        # Insert server specific sbatch commands before "### Script execution"
        pbs[-2:1] = SLURM_SBATCH
        return '\n'.join(pbs)

    def start(self, job):
        """Start job on SLURM server

        Returns:
            jobid_cluster on SLURM server
        """
        # Create PBS file
        pbs_file = job.jobid + '.pbs'
        with open(SLURM_PBS_PATH + pbs_file, 'w') as f:
            pbs = self.make_pbs(job)
            f.write(pbs)
        # Copy PBS file: "scp pbs vouws@tycho:~/name > /dev/null"
        cmd1 = ['scp', SLURM_PBS_PATH + pbs_file, self.ssh_arg + ':' + self.pbs_path + pbs_file]
        sp.check_output(cmd1, stderr=sp.STDOUT)
        # Create parameter file
        params_file = job.jobid + '.params'
        with open(PARAMS_PATH + params_file, 'w') as f:
            # parameters are a list of key=value, may instead be a json file
            params = job.parameters_to_text()
            # params = job.parameters_to_json()
            f.write(params)
        # Copy parameter file
        cmd2 = ['scp', PARAMS_PATH + params_file, self.ssh_arg + ':' + self.params_path + params_file]
        sp.check_output(cmd2, stderr=sp.STDOUT)
        # Start job: "ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x start -p ~/name'"
        cmd3 = ['ssh', self.ssh_arg, self.uws_handler, '-x start', '-p ' + self.pbs_path + pbs_file]
        jobid_cluster = sp.check_output(cmd3, stderr=sp.STDOUT)
        # TODO: change start time here?
        # Remove trailing \n from output
        return jobid_cluster[:-1]

    def abort(self, job):
        """Abort job on SLURM server"""
        # "ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x abort -p jobid'"
        cmd = ['ssh', self.ssh_arg, self.uws_handler, '-x abort', '-p ' + str(job.jobid_cluster)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def delete(self, job):
        """Delete job on SLURM server"""
        # "ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x delete -p jobid'"
        cmd = ['ssh', self.ssh_arg, self.uws_handler, '-x delete', '-p ' + str(job.jobid_cluster)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def get_status(self, job):
        """Get job status (phase) from SLURM server

        Returns:
            job status (phase)
        """
        # "ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid'"
        cmd = ['ssh', self.ssh_arg, self.uws_handler, '-x status', '-p ' + str(job.jobid_cluster)]
        phase = sp.check_output(cmd, stderr=sp.STDOUT)
        # TODO: change end time here if phase is COMPLETED?
        # Remove trailing \n from output
        return phase[:-1]

    def get_start_time(self, job):
        """Get job start time from SLURM server

        Returns:
            start time in ISO format
        """
        # "ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid'"
        cmd = ['ssh', self.ssh_arg, self.uws_handler, '-x start_time', '-p ' + str(job.jobid_cluster)]
        end_time = sp.check_output(cmd, stderr=sp.STDOUT)
        # Remove trailing \n from output,and replace ' ' by 'T' in ISO date
        return end_time[:-1].replace(' ','T')

    def get_end_time(self, job):
        """Get job end time from SLURM server

        Returns:
            end time in ISO format
        """
        # "ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid'"
        cmd = ['ssh', self.ssh_arg, self.uws_handler, '-x end_time', '-p ' + str(job.jobid_cluster)]
        end_time = sp.check_output(cmd, stderr=sp.STDOUT)
        # Remove trailing \n from output,and replace ' ' by 'T' in ISO date
        return end_time[:-1].replace(' ','T')
