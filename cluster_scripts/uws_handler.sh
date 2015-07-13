#!/bin/bash

parameter='undefined'
# For tycho
#wd='/scratch/vouws/uwsdata'
#rd='/poubelle/vouws/uwsdata'
# For quadri12
wd='/obs/vouws/scratch'
rd='/obs/vouws/poubelle'

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
      if [ $? = 0 ]; then
         mkdir $wd/$run_id
         mkdir $rd/$run_id
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
   if [ -d $wd/${parameter} ]; then
      scancel ${parameter}
      touch $rd/${parameter}/aborted
      exit 0
   else
      exit 1
   fi
fi


if [ ${action} = 'delete' ]; then
   if [ -f $wd/${parameter}/start ]; then
      scancel ${parameter}
      rm -rf $wd/${parameter}
      exit 0
   else
      # uws->init() has not been called...
      echo "start file not found, nothing to delete?"
      exit 1 
   fi
fi


if [ ${action} = 'status' ]; then
   if [ -f $rd/${parameter}/done ]; then
      if [ -d $rd/${parameter}/results ]; then
         # Copy results to UWS server
         # scp -r $rd/${parameter} www@voparis-uws.obspm.fr:/share/web/data/uwsdata/
         phase="COMPLETED"
      else
         phase="ERROR"
      fi
   elif [ -f $wd/${parameter}/error ]; then
      phase="ERROR"
   else
      phase=`squeue -j ${parameter}  -o "%i %.11T" 2>/dev/null | grep ${parameter} | awk '{print $2}'`
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
   if [ -f $rd/${parameter}/start ]; then
      start_time=`stat -c %y $rd/${parameter}/start | cut -d'.' -f1`
      echo $start_time
      exit 0
   else
      exit 1 
   fi
fi

if [ ${action} = 'end_time' ]; then
   if [ -f $rd/${parameter}/done ]; then
      end_time=`stat -c %y $rd/${parameter}/done | cut -d'.' -f1`
      echo $end_time
      exit 0
   elif [ -f $rd/${parameter}/aborted ]; then
      end_time=`stat -c %y $rd/${parameter}/aborted | cut -d'.' -f1`
      echo $end_time
      exit 0
   elif [ -f $wd/${parameter}/error ]; then
      end_time=`stat -c %y $wd/${parameter}/error | cut -d'.' -f1`
      echo $end_time
      exit 0
   else
      exit 1 
   fi
fi

