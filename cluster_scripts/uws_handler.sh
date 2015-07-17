#!/bin/bash

parameter='undefined'
# For tycho
#wd='/scratch/vouws/uwsdata'
#rd='/poubelle/vouws/uwsdata'
# For quadri12
wd='/obs/vouws/scratch'
rd='/obs/vouws/poubelle'

while getopts "x:i:p:w:r:" opt; do
   case $opt in
      x)
         action=$OPTARG
         ;;
      i)
         jobid=$OPTARG
         ;;
      p)
         pbs=$OPTARG
         ;;
      w)
         wd=$OPTARG
         ;;
      r)
         rd=$OPTARG
         ;;
      \?)
         echo "Invalid option: -$OPTARG" >&2
         exit 1
         ;;
   esac
done


if [ ${action} = 'start' ]; then
   if [ -f ${pbs} ]; then
      run_id=`sbatch ${pbs} | awk '{print $4}'`
      if [ $? = 0 ]; then
         echo $run_id
         exit 0
      else
         exit 1
      fi
   else
      exit 1
   fi
fi


if [ ${action} = 'abort' ]; then
   if [ -f ${rd}/start ]; then
      scancel ${jobid}
      touch ${rd}/aborted
      exit 0
   else
      echo "start file not found, nothing to abort?"
      exit 1
   fi
fi


if [ ${action} = 'delete' ]; then
   if [ -f ${rd}/start ]; then
      scancel ${jobid}
      rm -rf ${wd}
      exit 0
   else
      # uws->init() has not been called...
      echo "start file not found, nothing to delete?"
      exit 1 
   fi
fi


if [ ${action} = 'status' ]; then
   if [ -f ${rd}/done ]; then
      if [ -d ${rd}/results ]; then
         # Copy results to UWS server
         # scp -r $rd/${parameter} www@voparis-uws.obspm.fr:/share/web/data/uwsdata/
         phase="COMPLETED"
      else
         phase="ERROR"
      fi
   elif [ -f ${rd}/error ]; then
      phase="ERROR"
   else
      phase=`squeue -j ${jobid} -o "%i %.11T" 2>/dev/null | grep ${jobid} | awk '{print $2}'`
      if [ "${phase}" == "RUNNING" ]; then 
         phase="EXECUTING"
      fi
      if [  "${phase}" != "EXECUTING" ] && [ "${phase}" != "PENDING" ] && [ "${phase}" != "QUEUED" ]; then
            phase='UNKNOWN'
      fi
   fi
   # Return phase
   echo ${phase}
   exit 0
fi

if [ ${action} = 'start_time' ]; then
   if [ -f ${rd}/start ]; then
      start_time=`stat -c %y ${rd}/start | cut -d'.' -f1`
      echo $start_time
      exit 0
   else
      exit 1 
   fi
fi

if [ ${action} = 'end_time' ]; then
   if [ -f ${rd}/done ]; then
      end_time=`stat -c %y ${rd}/done | cut -d'.' -f1`
      echo $end_time
      exit 0
   elif [ -f ${rd}/aborted ]; then
      end_time=`stat -c %y ${rd}/aborted | cut -d'.' -f1`
      echo $end_time
      exit 0
   elif [ -f ${rd}/error ]; then
      end_time=`stat -c %y ${rd}/error | cut -d'.' -f1`
      echo $end_time
      exit 0
   else
      exit 1 
   fi
fi

