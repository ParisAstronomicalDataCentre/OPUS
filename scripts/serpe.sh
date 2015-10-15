#!/bin/bash
# Utilisation des jetons IDL du LESIA
IDL_LMGRD_LICENSE_FILE=1700@jetons-lesia.obspm.fr:1700@jetons.obspm.fr
# Load IDL libs
SERPE_FRTEND_PATH='/obs/vouws/serpe'
SERPE_DATA_DIR='/obs/vouws/serpe/data'
SERPE_RESULT_DIR=$rd
#config='Io_21_01_2013.srp'
idlcmd="restore, '${SERPE_FRTEND_PATH}/SERPE.sav' & main"
echo ${config} | idl -e "$idlcmd"
