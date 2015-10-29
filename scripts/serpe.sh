#!/bin/bash
# Utilisation des jetons IDL du LESIA
IDL_LMGRD_LICENSE_FILE=1700@jetons-lesia.obspm.fr:1700@jetons.obspm.fr
# Load IDL libs
SERPE_FRTEND_PATH='/home/vouws/serpe'
SERPE_DATA_DIR='/home/vouws/serpe/data'
SERPE_RESULT_DIR=$wd
echo ${config}
idlcmd="restore, '${SERPE_FRTEND_PATH}/SERPE.sav' & main"
echo ${idlcmd}
# Run IDL command
echo ${config} | idl -e "$idlcmd"
