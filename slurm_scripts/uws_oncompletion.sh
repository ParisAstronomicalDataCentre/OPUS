#!/usr/bin/env bash
# To be executed by SLURM on completion of a job
# e.g. from /usr/local/sbin/completion_script.sh
uws_url="https://voparis-uws-test.obspm.fr/handler/job_event"
case "$JOBSTATE" in
    RUNNING)
        curl --max-time 10 -d jobid="$JOBID" -d phase="EXECUTING" --data-urlencode error_msg="Job failed" $uws_url
        ;;
    FAILED)
        error_msg="${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${FUNCNAME[1]}"
        curl --max-time 10 -d jobid="$JOBID" -d phase="ERROR" --data-urlencode error_msg="$error_msg" $uws_url
        ;;
    TIMEOUT)
        curl --max-time 10 -d jobid="$JOBID" -d phase="ERROR" -d error_msg="TIMEOUT" $uws_url
        ;;
    *)
        curl --max-time 10 -d jobid="$JOBID" -d phase="$JOBSTATE" $uws_url
        ;;
esac
