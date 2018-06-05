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
* get_jobdata
* cp_script
"""

import datetime as dt
import subprocess as sp
from .settings import *

if MANAGER == 'Local':
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
    get_jobdata() and cp_script().
    """

    jobdata_path = '.'
    scripts_path = '.'
    workdir_path = '.'
    results_path = '.'

    def _make_batch(self, job, jobid_var='$$'):
        """Make batch file to run the job and signal status to the UWS server directly

        Returns:
            batch file content as a string
        """
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        wd = '{}/{}'.format(self.workdir_path, job.jobid)
        rs = '{}/{}'.format(self.results_path, job.jobid)
        # Need JDL for results description
        if not job.jdl.content:
            job.jdl.read(job.jobname)
        # Create sbatch
        batch = [
            '### INIT',
            'JOBID={}'.format(jobid_var),
            'echo "JOBID is $JOBID"',
            'timestamp() {',
            '    date +"%Y-%m-%dT%H:%M:%S"',
            '}',
            'echo "[`timestamp`] Initialize job"',
        ]
        # Error/Suspend/Term handler (send signals to server with curl)
        batch.extend([
            #'set -e ',
            'job_event() {',
            '    if [ -z "$2" ]',
            '    then',
            '        curl -k -s -o $jd/curl_$1_signal.log'
            ' -d "jobid=$JOBID" -d "phase=$1" {}/handler/job_event'.format(BASE_URL),
            '    else',
            '        echo "$1 $2"',
            '        curl -k -s -o $jd/curl_$1_signal.log'
            ' -d "jobid=$JOBID" -d "phase=$1" --data-urlencode "error_msg=$2" {}/handler/job_event'.format(BASE_URL),
            '    fi',
            '}',
            'error_handler() {',
            '    touch $jd/error',
            '    copy_results',
            '    msg="Error in ${BASH_SOURCE[1]##*/} running command: $BASH_COMMAND"',
            '    job_event "ERROR" "$msg"',
            '    rm -rf $wd',
            '    trap - SIGHUP SIGINT SIGQUIT SIGTERM ERR',
            '    exit 1',
            '}',
            'term_handler() {',
            '    touch $jd/error',
            '    copy_results',
            '    msg="Early termination in ${BASH_SOURCE[1]##*/} (signal $1 received)"',
            '    job_event "ERROR" "$msg"',
            '    rm -rf $wd',
            '    trap - SIGHUP SIGINT SIGQUIT SIGTERM ERR',
            '    exit 1',
            '}',
            'for sig in SIGHUP SIGINT SIGQUIT SIGTERM; do',
            '     trap "term_handler $sig" $sig',
            ' done',
            'trap "error_handler" ERR',
            #'trap "term_handler" SIGHUP SIGINT SIGQUIT SIGTERM',
        ])
        # Function to copy results from wd to jd
        cp_results = [
            'copy_results() {',
        ]
        for rname, r in job.jdl.content.get('generated', {}).items():
            # TODO: copy directly to archive directory (?)
            fname = job.get_result_filename(rname)
            line = [
                '    if [ -f $wd/{fname} ]; then',
                "        hash=`shasum -a " + SHA_ALGO + " $wd/{fname} | awk '{{print $1}}'`",
                '        echo {rname}: >> $jd/results.yml',
                '        echo "  file_name: {fname}" >> $jd/results.yml',
                '        echo "  file_dir: $rs" >> $jd/results.yml',
                '        echo "  content_type: {rtype}" >> $jd/results.yml',
                '        echo "  hash: "$hash >> $jd/results.yml',
                '        echo "Found and copied: {rname}={fname}";',
                '        cp $wd/{fname} $rs/{fname};',
                '    else',
                '        echo "NOT FOUND: {rname}={fname}"',
                '    fi',
            ]
            cp_results.append('\n'.join(line).format(rname=rname, fname=fname, rtype=r['content_type']))
            # cp_results.append(
            #     '    [ -f $wd/{fname} ]'
            #     ' && {{ cp $wd/{fname} $rs; echo "Found and copied: {rname}={fname}"; }}'
            #     ' || echo "NOT FOUND: {rname}={fname}"'
            #     ''.format(rname=rname, fname=fname)
            # )
        cp_results.append(
            '}',
        )
        batch.extend(cp_results)
        # Set $wd and $jd
        batch.extend([
            '### PREPARE DIRECTORIES',
            'jd={}'.format(jd),
            'wd={}'.format(wd),
            'rs={}'.format(rs),
            'cp {}/{}.sh $jd'.format(self.scripts_path, job.jobname),
            'mkdir -p $rs',
            'cd $wd',
            # 'echo "User is `id`"',
            # 'echo "Working dir is $wd"',
            # 'echo "JobData dir is $jd"',
            # Move uploaded files to working directory if they exist
            #'echo "[`timestamp`] Prepare input files"',
            #'for filename in $up/*; do [ -f "$filename" ] && cp $filename $wd; done',
        ])
        # Execution
        batch.extend([
            '### EXECUTION',
            'job_event "EXECUTING"',
            'echo "[`timestamp`] ***** Start job *****"',
            'touch $jd/start',
            # Load variables from params file
            '. $jd/parameters.sh',
            # Run script in the current environment
            '. $jd/{}.sh'.format(job.jobname),
            '### COPY RESULTS',
            'echo "[`timestamp`] List files in workdir"',
            'ls -oht',
            'echo "[`timestamp`] Copy results"',
            'copy_results',
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
        :return: process_id, jobid on work cluster
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

    def get_jobdata(self, job):
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
    Note that get_status(), get_info(), get_jobdata() and cp_script() functions
    are not needed as the job runs on the UWS server directly
    """
    poll_interval = 2  # poll processes regularly to avoid zombies
    suspended_processes = []  # suspended processes, restart signals will be sent regularly

    def __init__(self):
        # PATHs
        self.scripts_path = SCRIPTS_PATH
        self.jobdata_path = JOBDATA_PATH
        self.workdir_path = LOCAL_WORKDIR_PATH
        self.results_path = RESULTS_PATH

    def _send_signal(self, process_id, phase, error_msg=''):
        data = {'jobid': process_id, 'phase': phase}
        if error_msg:
            data['error_msg'] = error_msg
        url = '{}/handler/job_event'.format(BASE_URL)
        response = requests.post(url, data)
        logger.info('job event sent {}'.format(response.content))
        if response.status_code != 200:
            logger.error(response.content)
        del response

    def _poll_process(self, popen, job):
        rcode = popen.poll()
        process_id = popen.pid
        # Actions depending on rcode value
        if not rcode:
            try:
                p = psutil.Process(process_id)
            except psutil.NoSuchProcess as e:
                logger.info('process {} ended (NoSuchProcess)'.format(process_id))
                if job.phase == 'EXECUTING':
                    self._send_signal(process_id, 'ERROR', error_msg='Process terminated with errors')
                return
            # TODO: Handle sleeping, idle, suspended processes?...
            # Handle stopped processes
            if p.status() in [psutil.STATUS_STOPPED, psutil.STATUS_TRACING_STOP]:
                logger.info('process {} stopped'.format(process_id))
                try:
                    # Try to restart the process by sending SIGCONT
                    os.kill(process_id, signal.SIGCONT)
                except OSError as e:
                    if 'No such process' in str(e):
                        logger.warning('No such process ({})'.format(process_id))
                    else:
                        logger.warning(str(e))
                if p.status() == psutil.STATUS_STOPPED:
                    # If this did not work, change status to SUSPENDED for now
                    self._send_signal(process_id, 'SUSPENDED')
                    self.suspended_processes.append(process_id)
                else:
                    # If this worked, continue execution
                    if process_id in self.suspended_processes:
                        self._send_signal(process_id, 'EXECUTING')
                        self.suspended_processes.remove(process_id)
                    logger.info('process {} continued'.format(process_id))
                # Rerun _poll_process after some time
                threading.Timer(self.poll_interval, self._poll_process, [popen, job]).start()
            else:
                # Let the process run
                logger.info('process {} running'.format(process_id))
                # Rerun _poll_process after some time
                threading.Timer(self.poll_interval, self._poll_process, [popen, job]).start()
        # Handle killed processes
        elif rcode == -9:
            logger.info('process {} killed during execution'.format(process_id))
            self._send_signal(process_id, 'ERROR', error_msg='Process killed during execution')
        # Handle processes terminated with errors
        elif rcode <= -1:
            logger.info('process {} terminated with errors'.format(process_id))
            self._send_signal(process_id, 'ERROR', error_msg='Process terminated with errors')
        # Otherwise process has terminated
        else:
            logger.info('process {} terminated (rcode=0)'.format(process_id))
            if job.phase == 'EXECUTING':
                self._send_signal(process_id, 'ERROR', error_msg='Process terminated (rcode=0)')

    def start(self, job):
        """Start job locally
        :return: process_id
        """
        # Make directories if needed
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        wd = '{}/{}'.format(self.workdir_path, job.jobid)
        if not os.path.isdir(jd):
            os.makedirs(jd)
        if not os.path.isdir(wd):
            os.makedirs(wd)
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
                '{}/{}/{}'.format(UPLOADS_PATH, job.jobid, fname),
                '{}/{}'.format(wd, fname))
        for furl in files['URI']:
            fname = furl.split('/')[-1]
            response = requests.get(furl, stream=True)
            with open('{}/{}'.format(wd, fname), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
        # Create batch file
        batch = [
            '#!/bin/bash -l',
            '### INIT LocalManager',
            # Redirect stdout and stderr to files
            'exec >{jd}/stdout.log 2>{jd}/stderr.log'.format(jd=jd),
        ]
        batch.extend(
            self._make_batch(job)
        )
        batch_file = '{}/batch.sh'.format(jd)
        with open(batch_file, 'w') as f:
            f.write('\n'.join(batch))
        os.chmod(batch_file, 0o744)
        # Execute batch using sp
        cmd = [batch_file]
        # logger.debug(' '.join(cmd))
        popen = sp.Popen(cmd)
        # poll popen regularly
        self._poll_process(popen, job)
        # Return process_id
        return popen.pid

    def abort(self, job):
        """Abort/Cancel job"""
        try:
            os.kill(job.process_id, signal.SIGKILL) # SIGTERM => error sent ; SIGKILL => no error sent, just killed!
        except OSError as e:
            if 'No such process' in str(e):
                logger.info('No such process ({}) for job {} {}'.format(job.process_id, job.jobname, job.jobid))
            else:
                logger.info(str(e))
        except:
            raise

    def delete(self, job):
        """Delete job"""
        # jobdata is already deleted by the server
        try:
            os.kill(job.process_id, signal.SIGKILL) # SIGTERM => error sent ; SIGKILL => no error sent, just killed!
        except OSError as e:
            if 'No such process' in str(e):
                logger.info('No such process ({}) for job {} {}'.format(job.process_id, job.jobname, job.jobid))
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

    def __init__(self):
        # Set basic attributes
        self.host = SLURM_URL
        self.user = SLURM_USER
        self.mail = SLURM_MAIL_USER
        self.ssh_arg = self.user + '@' + self.host
        # PATHs
        self.scripts_path = SLURM_SCRIPTS_PATH
        self.jobdata_path = SLURM_JOBDATA_PATH
        self.workdir_path = SLURM_WORKDIR_PATH
        self.results_path = SLURM_RESULTS_PATH

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
            '### INIT SLURM',
            '#SBATCH --job-name={}'.format(job.jobname),
            '#SBATCH --error={}/stderr.log'.format(jd),
            '#SBATCH --output={}/stdout.log'.format(jd),
            '#SBATCH --mail-user={}'.format(self.mail),
            '#SBATCH --mail-type=ALL',
            '#SBATCH --no-requeue',
            '#SBATCH --time={}'.format(duration_str),
        ]
        # Insert server/job specific sbatch commands
        for k in SLURM_SBATCH_DEFAULT:
            # Check if parameter is given in job.parameters or use default
            v = job.parameters.get('slurm_'+k, SLURM_SBATCH_DEFAULT[k])
            sbatch.append('#SBATCH --{}={}'.format(k, v))
        for k in SLURM_PARAMETERS:
            if k not in SLURM_SBATCH_DEFAULT:
                if 'slurm_'+k in job.parameters:
                    v = job.parameters.get('slurm_'+k, SLURM_SBATCH_DEFAULT[k])
                    sbatch.append('#SBATCH --{}={}'.format(k, v))
        # Script init and execution
        sbatch.extend(
            self._make_batch(job, jobid_var='$SLURM_JOBID')
        )
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
            process_id on SLURM server
        """
        # Create jobdata and workdir (to upload the scripts, parameters and input files)
        jd = '{}/{}'.format(self.jobdata_path, job.jobid)
        wd = '{}/{}'.format(self.workdir_path, job.jobid)
        cmd = ['ssh', '-v', self.ssh_arg,
               'mkdir -p {{{jd},{wd}}}'.format(jd=jd, wd=wd)]
        # logger.debug(' '.join(cmd))
        try:
            sp.check_output(cmd, stderr=sp.STDOUT, universal_newlines=True)
        except sp.CalledProcessError as e:
            logger.warning('{}: {}'.format(e.cmd, e.output))
            if 'File exists' in str(e.output):
                logger.warning('force start {} {} (directories exist)'.format(job.jobname, job.jobid))
            else:
                raise
        # Create parameter file
        param_file_local = '{}/{}_parameters.sh'.format(TEMP_PATH, job.jobid)
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
        # Copy input files to workdir_path (scp if uploaded from form, or wget if given as a URI)
        # TODO: delete files
        for fname in files['form']:
            cmd = ['scp',
                   '{}/{}/{}'.format(UPLOADS_PATH, job.jobid, fname),
                   '{}:{}/{}'.format(self.ssh_arg, wd, fname)]
            # logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)
        for furl in files['URI']:
            fname = furl.split('/')[-1]
            cmd = ['ssh', self.ssh_arg,
                   'wget -q {} -O {}/{}'.format(furl, wd, fname)]
            # logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)
        # Create sbatch file
        sbatch_file_local = '{}/{}_sbatch.sh'.format(TEMP_PATH, job.jobid)
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
        process_id = str(sp.check_output(cmd, stderr=sp.STDOUT))
        # Get process_id from output (e.g. "Submitted batch job 9421")
        return process_id.split(' ')[-1]

    def abort(self, job):
        """Abort job on SLURM server"""
        cmd = ['ssh', self.ssh_arg,
               'scancel {}'.format(job.process_id)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def delete(self, job):
        """Delete job on SLURM server"""
        if job.phase not in ['COMPLETED', 'ERROR']:
            cmd = ['ssh', self.ssh_arg,
                   'scancel {}'.format(job.process_id)]
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
        # Delete results_path
        cmd = ['ssh', self.ssh_arg,
               'rm -rf {}/{}'.format(self.results_path, job.jobid)]
        sp.check_output(cmd, stderr=sp.STDOUT)

    def get_status(self, job):
        """Get job status (phase) from SLURM server

        Returns:
            job status (phase)
        """
        cmd = ['ssh', self.ssh_arg,
               'sacct -j {}'.format(job.process_id),
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
               'sacct -j {}'.format(job.process_id),
               '-o jobid,start,end,elapsed,state -P -n']
        logger.debug(' '.join(cmd))
        info = sp.check_output(cmd, stderr=sp.STDOUT)
        info_dict = info.split('|')
        return info_dict

    def get_jobdata(self, job):
        """Get job results from SLURM server

        Returns:
            list of results?
        """
        # Retrieve jobdata (scripts used, stdout/err...)
        cmd = ['scp', '-rp',
               '{}:{}/{}'.format(self.ssh_arg, self.jobdata_path, job.jobid),
               JOBDATA_PATH]
        logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)
        # Retrieve results
        if COPY_RESULTS:
            cmd = ['scp', '-rp',
                   '{}:{}/{}'.format(self.ssh_arg, self.results_path, job.jobid),
                   RESULTS_PATH]
            logger.debug(' '.join(cmd))
            sp.check_output(cmd, stderr=sp.STDOUT)

    def cp_script(self, jobname):
        """Copy job script to SLURM server"""
        cmd = ['scp',
               '{}/{}.sh'.format(SCRIPTS_PATH, jobname),
               '{}:{}/{}.sh'.format(self.ssh_arg, self.scripts_path, jobname)]
        logger.debug(' '.join(cmd))
        sp.check_output(cmd, stderr=sp.STDOUT)
