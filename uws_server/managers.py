#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Defines the Manager classes that defines the interfaces between the UWS server
and the job manager (e.g. SLURM)

Specific functions are expected for those classes:
* start
* abort
* delete
* get_status
* get_info
* get_results
* cp_script
"""

import datetime as dt
import subprocess as sp
from settings import *


# -------------
# Manager class


class Manager(object):
    """
    Manage job execution on cluster. This class defines required functions executed
    by the UWS server: start(), abort(), delete(), get_status(), get_info(),
    get_results() and cp_script().
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

    def get_results(self, job):
        """Get job results from cluster"""
        pass

    def cp_script(self, jobname):
        """Copy job script to cluster"""
        pass


class SLURMManager(Manager):
    """Manage interactions with SLURM queue manager (e.g. on tycho.obspm.fr)"""

    def __init__(self, host=SLURM_URL, user=SLURM_USER, home=SLURM_HOME_PATH, mail=SLURM_USER_MAIL,
                 jobdata_path=SLURM_JOBDATA_PATH, workdir_path=SLURM_WORKDIR_PATH):
        # Set basic attributes
        self.host = host
        self.user = user
        self.home = home
        self.mail = mail
        self.ssh_arg = user + '@' + host
        # PATHs
        self.scripts_path = '{}/scripts'.format(home)
        self.jobdata_path = jobdata_path
        self.workdir_path = workdir_path

    def _make_sbatch(self, job):
        """Make sbatch file content for given job

        Returns:
            sbatch file content as a string
        """
        duration = dt.timedelta(0, int(job.execution_duration))
        # duration format is 00:01:00 for 1 min
        duration_str = str(duration).replace(' days', '').replace(' day', '').replace(', ', '-')
        # Create sbatch
        sbatch = [
            '#!/bin/bash -l',
            '#SBATCH --job-name={}'.format(job.jobname),
            '#SBATCH --error={}/{}/results/stderr.log'.format(self.jobdata_path, job.jobid),
            '#SBATCH --output={}/{}/results/stdout.log'.format(self.jobdata_path, job.jobid),
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
            'timestamp() {',
            '    date +"%Y-%m-%dT%H:%M:%S"',
            '}',
            'echo "[`timestamp`] Initialize job"',
            # Error handler (send signal on error, in addition to job completion by SLURM)
            'set -e ',
            'error_handler() {',
            '    touch $jd/error',
            # '    error_string=`tac /obs/vouws/uws_logs/$SLURM_JOBID.err | grep -m 1 .`',
            # '    msg="${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${FUNCNAME[1]}"',
            '    msg="Error in ${BASH_SOURCE[1]##*/} running command: $BASH_COMMAND"',
            '    echo "$msg"', # echo in stdout log
            # '    echo "Signal error"',
            '    curl -k -s -o $jd/curl_error_signal.log '
            '        -d "jobid=$SLURM_JOBID" -d "phase=ERROR" --data-urlencode "error_msg=$msg" '
            '        {}/handler/job_event'.format(BASE_URL),
            '    rm -rf $wd',
            # '    echo "Remove trap"',
            '    trap - INT TERM EXIT',
            '    exit 1',
            '}',
            'trap "error_handler" INT TERM EXIT',
            # Set $wd and $jd
            'wd={}/{}'.format(self.workdir_path, job.jobid),
            'jd={}/{}'.format(self.jobdata_path, job.jobid),
            'mkdir -p $wd',
            'cd $wd',
            'echo "SLURM_JOBID is $SLURM_JOBID"',
            #'echo "User is `id`"',
            #'echo "Working dir is $wd"',
            #'echo "JobData dir is $jd"',
            # Move uploaded files to working directory if they exist
            'echo "[`timestamp`] Prepare input files"',
            'for filename in $jd/input/*; do [ -f "$filename" ] && cp $filename $wd; done',
            # Start job
            'curl -k -s -o $jd/curl_start_signal.log '
            '    -d "jobid=$SLURM_JOBID" -d "phase=RUNNING" '
            '    {}/handler/job_event'.format(BASE_URL),
            'echo "[`timestamp`] ***** Start job *****"',
            'touch $jd/start',
            '### EXEC',
            # Load variables from params file
            '. {}/{}/parameters.sh'.format(self.jobdata_path, job.jobid),
            # Run script in the current environment (with SLURM_JOBID defined)
            'cp {}/{}.sh $jd'.format(self.scripts_path, job.jobname),
            '. {}/{}.sh'.format(self.scripts_path, job.jobname),
            'echo "[`timestamp`] List files in workdir"',
            'ls -l',
            '### CP RESULTS',
            #'mkdir $jd/results',
        ])
        # Need JDL for results description
        if not job.jdl.content:
            job.jdl.read(job.jobname)
        # Identify results to be moved to $jd/results
        cp_results = [
            'echo "[`timestamp`] Copy results"'
        ]
        for rname, r in job.jdl.content['results'].iteritems():
            fname = job.get_result_filename(rname)
            cp_results.append(
                '[ -f $wd/{fname} ] '
                '&& {{ cp $wd/{fname} $jd/results; echo "Found and copied: {rname}={fname}"; }} '
                '|| echo "NOT FOUND: {rname}={fname}"'
                ''.format(rname=rname, fname=fname)
            )
        sbatch.extend(cp_results)
        # Clean and terminate job
        sbatch.extend([
            '### CLEAN',
            'rm -rf $wd',
            'touch $jd/done',
            'echo "[`timestamp`] ***** Job done *****"',
            'trap - INT TERM EXIT',
            'exit 0',
        ])
        # On completion, SLURM executes the script /usr/local/sbin/completion_script.sh
        # """
        # # vouws
        # if [[ "$UID" -eq 1834 ]]; then
        #     curl -k --max-time 10 -d jobid="$JOBID" -d phase="$JOBSTATE" https://voparis-uws-test.obspm.fr/handler/job_event
        # fi
        # """
        return '\n'.join(sbatch)

    def start(self, job):
        """Start job on SLURM server

        Returns:
            jobid_cluster on SLURM server
        """
        # Create jobdata dir (to upload the scripts, parameters and input files)
        cmd = ['ssh', self.ssh_arg,
               'mkdir -p {}/{}/{{input,results}}'.format(self.jobdata_path, job.jobid)]
        # logger.debug(' '.join(cmd))
        try:
            sp.check_output(cmd, stderr=sp.STDOUT)
        except sp.CalledProcessError as e:
            logger.warning('{}: {}'.format(e.cmd, e.output))
            if 'File exists' in e.output:
                logger.warning('force start {} {} (directories exist)'.format(job.jobname, job.jobid))
            else:
                raise
        # Create parameter file
        param_file_local = '{}/{}_parameters.sh'.format(SBATCH_PATH, job.jobid)
        param_file_distant = '{}/{}/parameters.sh'.format(self.jobdata_path, job.jobid)
        with open(param_file_local, 'w') as f:
            # parameters are a list of key=value (easier for bash sourcing)
            params, files = job.parameters_to_bash(get_files=True)
            f.write(params)
        # Copy parameter file to jobdata_path
        cmd = ['scp',
               param_file_local,
               '{}:{}'.format(self.ssh_arg, param_file_distant)]
        # logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)
        # Copy files to workdir_path (scp if uploaded from form, or wget if given as a URI)
        # TODO: delete files
        for fname in files['form']:
            cmd = ['scp',
                   '{}/{}/{}'.format(UPLOAD_PATH, job.jobid, fname),
                   '{}:{}/{}/input/{}'.format(self.ssh_arg, self.jobdata_path, job.jobid, fname)]
            # logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)
        for furl in files['URI']:
            fname = furl.split('/')[-1]
            cmd = ['ssh', self.ssh_arg,
                   'wget -q {} -O {}/{}/input/{}'.format(furl, self.jobdata_path, job.jobid, fname)]
            # logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)
        # Create sbatch file
        sbatch_file_local = '{}/{}_sbatch.sh'.format(SBATCH_PATH, job.jobid)
        sbatch_file_distant = '{}/{}/sbatch.sh'.format(self.jobdata_path, job.jobid)
        with open(sbatch_file_local, 'w') as f:
            sbatch = self._make_sbatch(job)
            f.write(sbatch)
        # Copy sbatch file to jobdata_path
        cmd = ['scp',
               sbatch_file_local,
               '{}:{}'.format(self.ssh_arg, sbatch_file_distant)]
        # logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)
        # Start job using sbatch
        cmd = ['ssh', self.ssh_arg,
               'sbatch {}'.format(sbatch_file_distant)]
        # logger.debug(' '.join(cmd))
        jobid_cluster = sp.check_output(cmd, stderr=sp.STDOUT)
        # Get jobid_cluster from output (e.g. "Submitted batch job 9421")
        return jobid_cluster.split(' ')[-1]

    def abort(self, job):
        """Abort job on SLURM server"""
        cmd = ['ssh', self.ssh_arg,
               'scancel {}'.format(job.jobid_cluster)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def delete(self, job):
        """Delete job on SLURM server"""
        if job.phase not in ['COMPLETED', 'ERROR']:
            cmd = ['ssh', self.ssh_arg,
                   'scancel {}'.format(job.jobid_cluster)]
            try:
                sp.check_output(cmd, stderr=sp.STDOUT)
            except sp.CalledProcessError as e:
                logger.warning('{}: {}'.format(e.cmd, e.output))
                if 'Invalid job id specified' in e.output:
                    logger.warning('force delete {} {}'.format(job.jobname, job.jobid))
                else:
                    raise
        # Delete workdir_path
        cmd = ['ssh', self.ssh_arg,
               'rm -rf {}/{}'.format(self.workdir_path, job.jobid)]
        sp.check_output(cmd, stderr=sp.STDOUT)
        # Delete jobdata_path
        cmd = ['ssh', self.ssh_arg,
               'rm -rf {}/{}'.format(self.jobdata_path, job.jobid)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def get_status(self, job):
        """Get job status (phase) from SLURM server

        Returns:
            job status (phase)
        """
        cmd = ['ssh', self.ssh_arg,
               'sacct -j {}'.format(job.jobid_cluster),
               '-o state -P -n']
        phase = sp.check_output(cmd, stderr=sp.STDOUT)
        # Take first line: there is a trailing \n in output, and possibly several lines
        phase = phase.split('\n')[0]
        return phase

    def get_info(self, job):
        """Get job info from SLURM server

        Returns:
            dictionary with info (jobid, start, end, elapsed, state)
        """
        # sacct -j 9000 -o jobid,start,end,elapsed,state -P -n
        cmd = ['ssh', self.ssh_arg,
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
        cmd = ['scp', '-rp',
               '{}:{}/jobdata/{}'.format(self.ssh_arg, SLURM_HOME_PATH, job.jobid),
               JOBDATA_PATH]
        logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)

    def cp_script(self, jobname):
        """Copy job script to SLURM server"""
        cmd = ['scp',
               '{}/{}.sh'.format(SCRIPT_PATH, jobname),
               '{}:{}/{}.sh'.format(self.ssh_arg, self.scripts_path, jobname)]
        logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)
