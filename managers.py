# -*- coding: utf-8 -*-
"""
Created on Tue May 11 2015

@author: mservillat
"""

import datetime as dt
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
        return job.phase

    def get_start_time(self, job):
        """Get job start time from SLURM server"""
        raise NotImplementedError('Manager does not support get_start_time()')

    def get_end_time(self, job):
        """Get job end time from cluster"""
        raise NotImplementedError('Manager does not support get_end_time()')


class SLURMManager(Manager):
    """Manage interactions with SLURM queue manager (e.g. on tycho.obspm.fr)"""

    def __init__(self, host=SLURM_URL, user=SLURM_USER, mail=SLURM_USER_MAIL):
        self.host = host
        self.user = user
        self.mail = mail
        self.ssh_arg = user + '@' + host
        # self.sbatch = sbatch
        self.pbs_path = 'uws_pbs/'
        self.params_path = 'uws_params/'
        self.working_path = '/obs/vouws/scratch/'
        self.results_path = '/obs/vouws/poubelle/'
        self.uws_handler = 'uws_scripts/uws_handler.sh'

    def _make_pbs(self, job):
        """Make PBS file content for given job

        Returns:
            PBS as a string
        """
        duration = dt.timedelta(0, job.execution_duration)
        # duration format is 00:01:00 for 1 min
        duration_str = str(duration).replace(' days', '').replace(' day', '').replace(', ', '-')
        pbs = [
            '#!/bin/sh',
            '#SBATCH --job-name={}'.format(job.jobname),
            '#SBATCH --error=/obs/vouws/uws_logs/%j.err',
            '#SBATCH --output=/obs/vouws/uws_logs/%j.job',
            '#SBATCH --mail-user=' + self.mail,
            '#SBATCH --mail-type=ALL',
            '#SBATCH --no-requeue',
            '#SBATCH --time=' + duration_str,
        ]
        # Insert server specific sbatch commands
        pbs.extend(SLURM_SBATCH_ADD)
        # Script init and execution
        pbs.extend([
            '### INIT',
            # Initially:
            #'/obs/vouws/uws_scripts/ctbin.pl 'voplus.obspm.fr/cta/events.fits' 5',
            # Init job execution
            'echo "Set die and trap"',
            'error_handler()',
            '{',
            '    echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${FUNCNAME[1]}"',
            '    exit 1',
            '}',
            'trap error_handler 1',
            'wd={}{}'.format(self.working_path, job.jobid),
            'rd={}{}'.format(self.results_path, job.jobid),
            'mkdir $wd',
            'mkdir $rd',
            'mkdir $rd/logs',
            'cd $wd',
            'echo "Working dir is $wd"',
            'echo "Results dir is $rd"',
            'curl -s -o $rd/logs/start_signal -d "jobid=$SLURM_JOBID" -d "phase=RUNNING" https://voparis-uws-test.obspm.fr/handler/job_event',
            'echo "Job started"',
            'touch $rd/start',
            '### EXEC',
            # Load variables from params file
            '. /obs/vouws/uws_params/{}.params'.format(job.jobid),
            # Run script in the current environment (with SLURM_JOBID defined)
            '. /obs/vouws/uws_scripts/{}.sh'.format(job.jobname),
            '### CLEAN',
            # TODO: Move logs to $rd/logs
            'cp /obs/vouws/uws_logs/$SLURM_JOBID.job $rd/logs',
            'cp /obs/vouws/uws_logs/$SLURM_JOBID.err $rd/logs',
            # TODO: Move results to $rd
            'mkdir $rd/results',
            'rm -rf $wd',
            'touch $rd/done',
            'echo "Job done"',
            #'curl -s -o $rd/logs/done_signal -d "jobid=$SLURM_JOBID" -d "phase=COMPLETED" https://voparis-uws-test.obspm.fr/handler/job_event',
        ])
        return '\n'.join(pbs)

    def start(self, job):
        """Start job on SLURM server

        Returns:
            jobid_cluster on SLURM server
        """
        # Create PBS file
        pbs_file = job.jobid + '.pbs'
        with open(SLURM_PBS_PATH + pbs_file, 'w') as f:
            pbs = self._make_pbs(job)
            f.write(pbs)
        # Copy PBS file: 'scp pbs vouws@tycho:~/name > /dev/null'
        cmd1 = ['scp', SLURM_PBS_PATH + pbs_file, self.ssh_arg + ':' + self.pbs_path + pbs_file]
        sp.check_output(cmd1, stderr=sp.STDOUT)
        # Create parameter file
        params_file = job.jobid + '.params'
        with open(PARAMS_PATH + params_file, 'w') as f:
            # parameters are a list of key=value, may instead be a json file
            params = job.parameters_to_text()
            # params = job.parameters_to_json()
            # TODO: wget files if param starts with http://
            f.write(params)
        # Copy parameter file
        cmd2 = ['scp', PARAMS_PATH + params_file, self.ssh_arg + ':' + self.params_path + params_file]
        sp.check_output(cmd2, stderr=sp.STDOUT)
        # Start job using uws_handler
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x start -p ~/name''
        cmd3 = ['ssh', self.ssh_arg, self.uws_handler,
                '-x start', '-p ' + self.pbs_path + pbs_file]
        jobid_cluster = sp.check_output(cmd3, stderr=sp.STDOUT)
        # Remove trailing \n from output
        return jobid_cluster[:-1]

    def abort(self, job):
        """Abort job on SLURM server"""
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x abort -p jobid''
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               '-x abort',
               '-i ' + str(job.jobid_cluster),
               '-r ' + self.results_path + job.jobid]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def delete(self, job):
        """Delete job on SLURM server"""
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x delete -p jobid''
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               '-x delete',
               '-i ' + str(job.jobid_cluster),
               '-r ' + self.results_path + job.jobid,
               '-w ' + self.working_path + job.jobid]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def get_status(self, job):
        """Get job status (phase) from SLURM server

        Returns:
            job status (phase)
        """
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid''
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               '-x status',
               '-i ' + str(job.jobid_cluster),
               '-r ' + self.results_path + job.jobid]
        phase = sp.check_output(cmd, stderr=sp.STDOUT)
        # TODO: change end time here if phase is COMPLETED?
        # Remove trailing \n from output
        return phase[:-1]

    def get_start_time(self, job):
        """Get job start time from SLURM server

        Returns:
            start time in ISO format
        """
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid''
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               '-x start_time',
               '-r ' + self.results_path + job.jobid]
        start_time = sp.check_output(cmd, stderr=sp.STDOUT)
        # Remove trailing \n from output,and replace ' ' by 'T' in ISO date
        return start_time[:-1].replace(' ','T')

    def get_end_time(self, job):
        """Get job end time from SLURM server

        Returns:
            end time in ISO format
        """
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid''
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               '-x end_time',
               '-r ' + self.results_path + job.jobid]
        end_time = sp.check_output(cmd, stderr=sp.STDOUT)
        # Remove trailing \n from output,and replace ' ' by 'T' in ISO date
        return end_time[:-1].replace(' ','T')
