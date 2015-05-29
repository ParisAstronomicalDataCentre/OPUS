#!/bin/bash

parameter='undefined'

while getopts "x:p:" opt; do
   case $opt in
      x)
         action=$OPTARG
         ;;
      p)
         parameter=$OPTARG
         ;;
      \?)
         echo "Invalid option: -$OPTARG" >&2
         exit 1
         ;;
   esac
done

if [ ${action} = 'start' ]; then
   if [ -f ${parameter} ]; then
      run_id=`sbatch ${parameter} | awk '{print $4}'`
      exit_code=$?
      echo $run_id
      mkdir /poubelle/vouws/uwsdata/$run_id
      exit ${exit_code}
   else
      exit 1
   fi
fi


if [ ${action} = 'abort' ]; then
   if [ -d /poubelle/vouws/uwsdata/${parameter} ]; then
      scancel ${parameter}
      exit 0
   else
      exit 1
   fi
fi


if [ ${action} = 'delete' ]; then
   if [ -d /poubelle/vouws/uwsdata/${parameter} ]; then
      scancel ${parameter}
      rm -rf /poubelle/vouws/uwsdata/${parameter}
      exit 0
   else
      # uws->init() has not been called...
      exit 1 
   fi
fi


if [ ${action} = 'status' ]; then
   phase=`squeue -j ${parameter}  -o "%i %.11T" | grep ${parameter} | awk '{print $2}'`
   if [ -f /poubelle/vouws/uwsdata/${parameter}/done ]; then
      if [ -d /poubelle/vouws/uwsdata/${parameter}/results ]; then
         scp -r /poubelle/vouws/uwsdata/${parameter} www@voparis-uws.obspm.fr:/share/web/data/uwsdata/
         phase="COMPLETED"
      else
         phase="ERROR"
      fi
      elif [ -f ~/uwsdata/${parameter}/error ]; then
         phase="ERROR"
      else
         if [ "${phase}" == "RUNNING" ]; then 
            phase="EXECUTING"
         fi
         if [  "${phase}" != "EXECUTING" ] && [ "${phase}" != "PENDING" ] && [ "${phase}" != "QUEUED" ]; then
            phase='UNKNOWN'
         fi
      fi

   echo ${phase}
   exit 0
fi
