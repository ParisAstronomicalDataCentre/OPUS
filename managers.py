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

    def get_info(self, job):
        """Get job info from cluster

        Returns:
            dictionary with job info
        """
        return job.phase

    def get_results(self, job):
        """Get job results from cluster"""


class SLURMManager(Manager):
    """Manage interactions with SLURM queue manager (e.g. on tycho.obspm.fr)"""

    def __init__(self, host=SLURM_URL, user=SLURM_USER, home=SLURM_HOME_PATH, mail=SLURM_USER_MAIL):
        self.host = host
        self.user = user
        self.home = home
        self.mail = mail
        self.ssh_arg = user + '@' + host
        # PATHs
        self.log_path = '{}/logs'.format(home)
        self.scripts_path = '{}/scripts'.format(home)
        self.sbatch_path = '{}/sbatch'.format(home)
        self.working_path = '{}/workdir'.format(home)  # may be a link on host
        self.jobdata_path = '{}/jobdata'.format(home)  # may be a link on host
        self.uws_handler = '{}/uws_handler.sh'.format(self.scripts_path)

    def _make_sbatch(self, job):
        """Make PBS file content for given job

        Returns:
            PBS as a string
        """
        duration = dt.timedelta(0, job.execution_duration)
        # duration format is 00:01:00 for 1 min
        duration_str = str(duration).replace(' days', '').replace(' day', '').replace(', ', '-')
        if not job.wadl:
            job.read_wadl()
        # Identify result filenames to move to $jd/results
        cp_results = []
        for rname, r in job.wadl['results'].iteritems():
            fname = job.get_result_filename(rname)
            cp_results.append('cp $wd/{} $jd/results'.format(fname))
        # scp results from cluster
        # uws_url = BASE_URL.split('//')[-1]
        # cp_results.append('scp -r $jd/results www@{}:{}/{}'.format(uws_url, RESULTS_PATH, job.jobid))
        # TODO: Identify parameters that need to be downloaded before processing
        #wget_filenames = { k: v['id1'] for k,v in a.items() if 'id1' in v }
        # Create PBS
        sbatch = [
            '#!/bin/bash',
            '#SBATCH --job-name={}'.format(job.jobname),
            '#SBATCH --error={}/%j.err'.format(self.log_path),
            '#SBATCH --output={}/%j.job'.format(self.log_path),
            '#SBATCH --mail-user=' + self.mail,
            '#SBATCH --mail-type=ALL',
            '#SBATCH --no-requeue',
            '#SBATCH --time=' + duration_str,
        ]
        # Insert server specific sbatch commands
        sbatch.extend(SLURM_SBATCH_ADD)
        # Script init and execution
        sbatch.extend([
            '### INIT',
            # Init job execution
            'wd={}/{}'.format(self.working_path, job.jobid),
            'jd={}/{}'.format(self.jobdata_path, job.jobid),
            'mkdir $wd',
            'mkdir $jd',
            'mkdir $jd/logs',
            'cd $wd',
            'echo "Working dir is $wd"',
            'echo "JobData dir is $jd"',
            'echo "Set trap"',
            'set -e ',
            'error_handler()',
            '{',
            '    touch $jd/error',
            #'    error_string=`tac /obs/vouws/uws_logs/$SLURM_JOBID.err | grep -m 1 .`',
            '    msg="Error in ${BASH_SOURCE[1]##*/} running command: $BASH_COMMAND"',  # ${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${FUNCNAME[1]}"'
            '    echo "$msg"',
            '    curl -s -o $jd/logs/error_signal '
            '        -d "jobid=$SLURM_JOBID" -d "phase=ERROR" --data-urlencode "error_msg=$msg" '
            '        {}/handler/job_event'.format(BASE_URL),
            '    rm -rf $wd',
            '    cp {}/$SLURM_JOBID.job $jd/logs/stdout.log'.format(self.log_path),
            '    cp {}/$SLURM_JOBID.err $jd/logs/stderr.log'.format(self.log_path),
            '    trap - INT TERM EXIT',
            '    exit 1',
            '}',
            'trap "error_handler" INT TERM EXIT',
            'echo "Signal start"',
            'curl -s -o $jd/logs/start_signal '
            '    -d "jobid=$SLURM_JOBID" -d "phase=RUNNING" '
            '    {}/handler/job_event'.format(BASE_URL),
            'echo "Job started"',
            'touch $jd/start',
            '### EXEC',
            # Load variables from params file
            '. {}/{}_parameters.sh'.format(self.sbatch_path, job.jobid),
            # Run script in the current environment (with SLURM_JOBID defined)
            '. {}/{}.sh'.format(self.scripts_path, job.jobname),
            '### CP RESULTS',
            'mkdir $jd/results',
        ])
        sbatch.extend(cp_results)
        sbatch.extend([
            '### CLEAN',
            'rm -rf $wd',
            'touch $jd/done',
            'echo "Job done"',
            # Move logs to $jd/logs
            'cp {}/$SLURM_JOBID.job $jd/logs/stdout.log'.format(self.log_path),
            'cp {}/$SLURM_JOBID.err $jd/logs/stderr.log'.format(self.log_path),
            'trap - INT TERM EXIT',
            'exit 0',
            #'curl -s -o $jd/logs/done_signal -d "jobid=$SLURM_JOBID" -d "phase=COMPLETED" https://voparis-uws-test.obspm.fr/handler/job_event',
        ])
        return '\n'.join(sbatch)

    def start(self, job):
        """Start job on SLURM server

        Returns:
            jobid_cluster on SLURM server
        """
        # Create PBS file
        sbatch_file_distant = '{}/{}.sh'.format(self.sbatch_path, job.jobid)
        sbatch_file_local = '{}/{}.sh'.format(SLURM_SBATCH_PATH, job.jobid)
        with open(sbatch_file_local, 'w') as f:
            sbatch = self._make_sbatch(job)
            f.write(sbatch)
        # Copy PBS file: 'scp sbatch vouws@tycho:~/name > /dev/null'
        cmd1 = ['scp',
                sbatch_file_local,
                '{}:{}'.format(self.ssh_arg, sbatch_file_distant)]
        # logger.debug(' '.join(cmd1))
        sp.check_output(cmd1, stderr=sp.STDOUT)
        # Create parameter file
        param_file_distant = '{}/{}_parameters.sh'.format(self.sbatch_path, job.jobid)
        param_file_local = '{}/{}_parameters.sh'.format(SLURM_SBATCH_PATH, job.jobid)
        with open(param_file_local, 'w') as f:
            # parameters are a list of key=value (easier for bash sourcing)
            params = job.parameters_to_text()
            # TODO: scp files if param starts with http:// or file://
            f.write(params)
            # TODO: set results as file names, to be copied after job completion
        # Copy parameter file
        cmd2 = ['scp',
                param_file_local,
                '{}:{}'.format(self.ssh_arg, param_file_distant)]
        # logger.debug(' '.join(cmd2))
        sp.check_output(cmd2, stderr=sp.STDOUT)
        # Start job using uws_handler
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x start -p ~/name''
        # cmd3 = ['ssh', self.ssh_arg, self.uws_handler,
        #         '-x start',
        #         '-p {}'.format(sbatch_file_distant)]
        cmd3 = ['ssh', self.ssh_arg,
                'sbatch {}'.format(sbatch_file_distant)]
        logger.debug(' '.join(cmd2))
        jobid_cluster = sp.check_output(cmd3, stderr=sp.STDOUT)
        # Get jobid_cluster from output (e.g. "Submitted batch job 9421")
        return jobid_cluster.split(' ')[-1]

    def abort(self, job):
        """Abort job on SLURM server"""
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x abort -p jobid''
        # cmd = ['ssh', self.ssh_arg, self.uws_handler,
        #        '-x abort',
        #        '-i ' + str(job.jobid_cluster),
        #        '-r {}/{}'.format(self.jobdata_path, job.jobid)]
        cmd = ['ssh', self.ssh_arg,
               'scancel {}'.format(job.jobid_cluster)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def delete(self, job):
        """Delete job on SLURM server"""
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x delete -p jobid''
        # cmd = ['ssh', self.ssh_arg, self.uws_handler,
        #        '-x delete',
        #        '-i ' + str(job.jobid_cluster),
        #        '-r {}/{}'.format(self.jobdata_path, job.jobid),
        #        '-w {}/{}'.format(self.working_path, job.jobid)]
        if job.phase not in ['COMPLETED', 'ERROR']:
            cmd1 = ['ssh', self.ssh_arg,
                    'scancel {}'.format(job.jobid_cluster)]
            sp.check_output(cmd1, stderr=sp.STDOUT)
        # Delete workdir
        cmd2 = ['ssh', self.ssh_arg,
                'rm -rf {}/{}'.format(self.working_path, job.jobid),]
        sp.check_output(cmd2, stderr=sp.STDOUT)
        # Delete jobdata
        cmd3 = ['ssh', self.ssh_arg,
                'rm -rf {}/{}'.format(self.jobdata_path, job.jobid),]
        sp.check_output(cmd3, stderr=sp.STDOUT)

    def get_status(self, job):
        """Get job status (phase) from SLURM server

        Returns:
            job status (phase)
        """
        # 'ssh vouws@tycho.obspm.fr '~/uws/uwshandler.sh -x status -p jobid''
        # cmd = ['ssh', self.ssh_arg, self.uws_handler,
        #        '-x status',
        #        '-i ' + str(job.jobid_cluster),
        #        '-r {}/{}'.format(self.jobdata_path, job.jobid)]
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               'sacct -j {}'.format(job.jobid_cluster),
               '-o state -P -n']
        phase = sp.check_output(cmd, stderr=sp.STDOUT)
        # TODO: change end time here if phase is COMPLETED?
        # Remove trailing \n from output
        return phase[:-1]

    def get_info(self, job):
        """Get job info from SLURM server

        Returns:
            dictionary with info (jobid, start, end, elapsed, state)
        """
        # sacct -j 9000 -o jobid,start,end,elapsed,state -P -n
        cmd = ['ssh', self.ssh_arg, self.uws_handler,
               'sacct -j {}'.format(job.jobid_cluster),
               '-o jobid,start,end,elapsed,state -P -n']
        logger.debug(' '.join(cmd))
        info = sp.check_output(cmd, stderr=sp.STDOUT)
        info_dict = info.split('|')
        return info_dict

    def get_results(self, job):
        """Get job results from SLURM server

        Returns:
            list of results?
        """
        # cp_results.append('scp -r $jd/results www@{}:{}/{}'.format(uws_url, JOBDATA_PATH, job.jobid))
        cmd = ['scp', '-rp',
               '{}:{}/jobdata/{}'.format(self.ssh_arg, SLURM_HOME_PATH, job.jobid),
               JOBDATA_PATH]
        # logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)
