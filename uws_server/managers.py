#!/usr/bin/env python2
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

if MANAGER == 'LocalManager':
    import shutil
    import signal
    import requests
    import threading
    import psutil

# -------------
# Manager class


class Manager(object):
    """
    Manage job execution. This class defines required functions executed
    by the UWS server: start(), abort(), delete(), get_status(), get_info(),
    get_results() and cp_script().
    """

    jobdata_path = '.'
    scripts_path = '.'
    workdir_path = '.'

    def _make_batch(self, job, jobid_var='$$'):
        """Make batch file to run the job and signal status to the UWS server directly

        Returns:
            batch file content as a string
        """
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        wd = '{}/{}'.format(self.workdir_path, job.jobid)
        # Create sbatch
        batch = [
            '### INIT',
            # Useful functions
            'timestamp() {',
            '    date +"%Y-%m-%dT%H:%M:%S"',
            '}',
            'job_event() {',
            '    if [ -z "$2" ]',
            '    then',
            '        curl -k -s -o $jd/curl_$1_signal.log'
            ' -d "jobid=$JOBID" -d "phase=$1" {}/handler/job_event'.format(BASE_URL),
            '    else',
            '        echo "$2"',
            '        curl -k -s -o $jd/curl_$1_signal.log '
            ' -d "jobid=$JOBID" -d "phase=$1" --data-urlencode "error_msg=$2" {}/handler/job_event'.format(BASE_URL),
            '    fi',
            '}',
            # Init JOBID
            'echo "[`timestamp`] Initialize job"',
            'JOBID={}'.format(jobid_var),
            'echo "JOBID is $JOBID"',
            # Set $wd and $jd
            'wd={}'.format(wd),
            'jd={}'.format(jd),
            'cp {}/{}.sh $jd'.format(self.scripts_path, job.jobname),
            'mkdir -p $wd',
            'cd $wd',
            # 'echo "User is `id`"',
            # 'echo "Working dir is $wd"',
            # 'echo "JobData dir is $jd"',
            # Error/Suspend/Term handler (send signals to server with curl)
            'set -e ',
            'error_handler() {',
            '    touch $jd/error',
            '    msg="Error in job ${BASH_SOURCE[1]##*/} running command: $BASH_COMMAND"',
            '    job_event "ERROR" "$msg"',
            '    trap - SIGHUP SIGINT SIGQUIT SIGTERM ERR',
            '    exit 1',
            '}',
            'term_handler() {',
            '    touch $jd/error',
            '    msg="Early termination of job ${BASH_SOURCE[1]##*/} running command: $BASH_COMMAND"',
            '    job_event "ERROR" "$msg"',
            #'    rm -rf $wd',
            '    trap - SIGHUP SIGINT SIGQUIT SIGTERM ERR',
            '    exit 1',
            '}',
            'trap "error_handler" ERR',
            'trap "term_handler" SIGHUP SIGINT SIGQUIT SIGTERM',
            # Move uploaded files to working directory if they exist
            'echo "[`timestamp`] Prepare input files"',
            'for filename in $jd/input/*; do [ -f "$filename" ] && cp $filename $wd; done',
            # Start job
            'job_event "EXECUTING"',
            'echo "[`timestamp`] ***** Start job *****"',
            'touch $jd/start',
            '### EXEC',
            # Load variables from params file
            '. $jd/parameters.sh',
            # Run script in the current environment
            '. $jd/{}.sh'.format(job.jobname),
            'echo "[`timestamp`] List files in workdir"',
            'ls -l',
            # 'mkdir $jd/results',
        ]
        # Need JDL for results description
        if not job.jdl.content:
            job.jdl.read(job.jobname)
        # Identify results to be moved to $jd/results
        cp_results = [
            '### CP RESULTS',
            'echo "[`timestamp`] Copy results"',
        ]
        for rname, r in job.jdl.content['results'].iteritems():
            fname = job.get_result_filename(rname)
            cp_results.append(
                '[ -f $wd/{fname} ] '
                '&& {{ cp $wd/{fname} $jd/results; echo "Found and copied: {rname}={fname}"; }} '
                '|| echo "NOT FOUND: {rname}={fname}"'
                ''.format(rname=rname, fname=fname)
            )
        batch.extend(cp_results)
        # Clean and terminate job
        batch.extend([
            '### CLEAN',
            'rm -rf $wd',
            'touch $jd/done',
            'echo "[`timestamp`] ***** Job done *****"',
            'trap - SIGHUP SIGINT SIGQUIT SIGTERM ERR',
            'job_event "COMPLETED"',
            'exit 0',
        ])
        return batch

    def start(self, job):
        """Start job
        :return: jobid_cluster, jobid on work cluster
        """
        # Make directories if needed
        # Create parameter file
        # Copy input files to workdir_path
        # Create batch file, e.g. batch = self._make_batch(job)
        # Execute batch
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
        return {'phase': job.phase}

    def get_results(self, job):
        """Get job results"""
        pass

    def cp_script(self, jobname):
        """Copy job script"""
        pass


# -------------
# Local Manager class


class LocalManager(Manager):
    """
    Manage job execution locally.
    Note that get_status(), get_info(), get_results() and cp_script() functions
    are not needed as the job runs on the UWS server directly
    """
    poll_interval = 4  # poll processes regularly to avoid zombies

    def __init__(self, jobdata_path=JOBDATA_PATH, script_path=SCRIPT_PATH):
        # PATHs
        self.jobdata_path = jobdata_path
        self.scripts_path = script_path
        self.workdir_path = '{}/../workdir'.format(jobdata_path)

    def _send_signal(self, pid, phase, error_msg=''):
        data = {'jobid': pid, 'phase': phase}
        if error_msg:
            data['error_msg'] = error_msg
        url = '{}/handler/job_event'.format(BASE_URL)
        response = requests.post(url, data)
        logger.info('job event sent {}'.format(response.content))
        if response.status_code != 200:
            logger.error(response.content)
        del response

    def _poll_process(self, popen):
        rcode = popen.poll()
        pid = popen.pid
        if not rcode:
            p = psutil.Process(pid)
            if p.status() == psutil.STATUS_STOPPED:
                logger.info('process {} stopped'.format(pid))
                # Try to restart process
                try:
                    os.kill(pid, signal.SIGCONT)
                    if p.status() == psutil.STATUS_STOPPED:
                        self._send_signal(pid, 'SUSPENDED')
                except:
                    self._send_signal(pid, 'SUSPENDED')
            else:
                logger.info('process {} running'.format(pid))
                threading.Timer(self.poll_interval, self._poll_process, [popen]).start()
        elif rcode == -9:
            logger.info('process {} killed'.format(pid))
            self._send_signal(pid, 'ERROR', error_msg='Process killed')
        elif rcode <= -1:
            logger.info('process {} terminated with errors'.format(pid))
        else:
            logger.info('process {} terminated'.format(pid))

    def start(self, job):
        """Start job locally
        :return: pid
        """
        # Make directories if needed
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        wd = '{}/{}'.format(self.workdir_path, job.jobid)
        if not os.path.isdir(jd):
            os.makedirs('{}/{}'.format(jd, 'input'))
            os.makedirs('{}/{}'.format(jd, 'results'))
        # Create parameter file
        param_file = '{}/parameters.sh'.format(jd)
        with open(param_file, 'w') as f:
            # parameters are a list of key=value (easier for bash sourcing)
            params, files = job.parameters_to_bash(get_files=True)
            f.write(params)
        os.chmod(param_file, 0o744)
        # Copy input files to workdir_path (scp if uploaded from form, or wget if given as a URI)
        # TODO: delete files
        for fname in files['form']:
            shutil.copy(
                '{}/{}/{}'.format(UPLOAD_PATH, job.jobid, fname),
                '{}/input/{}'.format(jd, fname))
        for furl in files['URI']:
            fname = furl.split('/')[-1]
            response = requests.get(furl, stream=True)
            with open('{}/input/{}'.format(jd, fname), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
        # Create batch file
        batch = [
            '#!/bin/bash -l',
            # Redirect stdout and stderr to files
            'exec >{jd}/results/stdout.log 2>{jd}/results/stderr.log'.format(jd=jd),
        ]
        batch.extend(self._make_batch(job))
        batch_file = '{}/batch.sh'.format(jd)
        with open(batch_file, 'w') as f:
            f.write('\n'.join(batch))
        os.chmod(batch_file, 0o744)
        # Execute batch using sp
        cmd = [batch_file]
        # logger.debug(' '.join(cmd))
        popen = sp.Popen(cmd)
        # poll popen regularly
        self._poll_process(popen)
        # Return pid
        return popen.pid

    def abort(self, job):
        """Abort/Cancel job"""
        try:
            os.kill(job.jobid_cluster, signal.SIGKILL) # SIGTERM => error sent ; SIGKILL => no error sent, just killed!
        except OSError as e:
            if 'No such process' in str(e):
                logger.info('No such process ({}) for job {} {}'.format(job.jobid_cluster, job.jobname, job.jobid))
            else:
                logger.info(str(e))
        except:
            raise

    def delete(self, job):
        """Delete job"""
        # jobdata is already deleted by the server
        try:
            os.kill(job.jobid_cluster, signal.SIGKILL) # SIGTERM => error sent ; SIGKILL => no error sent, just killed!
        except OSError as e:
            if 'No such process' in str(e):
                logger.info('No such process ({}) for job {} {}'.format(job.jobid_cluster, job.jobname, job.jobid))
            else:
                logger.info(str(e))
        except:
            raise


# -------------
# SLURM Manager class


class SLURMManager(Manager):
    """
    Manage interactions with SLURM queue manager (e.g. on tycho.obspm.fr)
    The ssh key should be placed in the .ssh/authorized_keys file on the SLURM work cluster for the account used
    """

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
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        duration = dt.timedelta(0, int(job.execution_duration))
        # duration format is 00:01:00 for 1 min
        duration_str = str(duration).replace(' days', '').replace(' day', '').replace(', ', '-')
        # Create sbatch
        sbatch = [
            '#!/bin/bash -l',
            '#SBATCH --job-name={}'.format(job.jobname),
            '#SBATCH --error={}/results/stderr.log'.format(jd),
            '#SBATCH --output={}/results/stdout.log'.format(jd),
            '#SBATCH --mail-user={}'.format(self.mail),
            '#SBATCH --mail-type=ALL',
            '#SBATCH --no-requeue',
            '#SBATCH --time={}'.format(duration_str),
        ]
        # Insert server specific sbatch commands
        for k, v in SLURM_SBATCH_DEFAULT.iteritems():
            sbline = '#SBATCH --{}={}'.format(k, v)
            sbatch.append(sbline)
        # Script init and execution
        sbatch.extend(self._make_batch(job, jobid_var='$SLURM_JOBID'))
        # On completion, SLURM executes the script /usr/local/sbin/completion_script.sh
        # """
        # # vouws
        # if [[ "$UID" -eq 1834 ]]; then
        #     curl -k --max-time 10 -d jobid="$JOBID" -d phase="$JOBSTATE" https://voparis-uws-test.obspm.fr/handler/job_event
        # fi
        # """
        return sbatch

    def start(self, job):
        """Start job on SLURM server

        Returns:
            jobid_cluster on SLURM server
        """
        # Create jobdata dir (to upload the scripts, parameters and input files)
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        cmd = ['ssh', self.ssh_arg,
               'mkdir -p {}/{{input,results}}'.format(jd)]
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
        param_file_distant = '{}/parameters.sh'.format(jd)
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
        # Copy inout files to workdir_path (scp if uploaded from form, or wget if given as a URI)
        # TODO: delete files
        for fname in files['form']:
            cmd = ['scp',
                   '{}/{}/{}'.format(UPLOAD_PATH, job.jobid, fname),
                   '{}:{}/input/{}'.format(self.ssh_arg, jd, fname)]
            # logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)
        for furl in files['URI']:
            fname = furl.split('/')[-1]
            cmd = ['ssh', self.ssh_arg,
                   'wget -q {} -O {}/input/{}'.format(furl, jd, fname)]
            # logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)
        # Create sbatch file
        sbatch_file_local = '{}/{}_sbatch.sh'.format(SBATCH_PATH, job.jobid)
        sbatch_file_distant = '{}/sbatch.sh'.format(jd)
        with open(sbatch_file_local, 'w') as f:
            sbatch = self._make_sbatch(job)
            f.write('\n'.join(sbatch))
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
        if phase in PHASE_CONVERT:
            phase = PHASE_CONVERT[phase]['phase']
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
               '{}:{}/{}'.format(self.ssh_arg, self.jobdata_path, job.jobid),
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
