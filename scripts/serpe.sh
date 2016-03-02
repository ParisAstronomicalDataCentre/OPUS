#!/bin/bash
# Utilisation des jetons IDL du LESIA
export IDL_LMGRD_LICENSE_FILE=1700@jetons-lesia.obspm.fr:1700@jetons.obspm.fr
# Load IDL libs
export SERPE_DATA_DIR=/maser/SERPE_SERVER/data/mfl/
echo "config=${config}"
idlcmd='restore, "/obs/vouws/scripts/serpe/SERPE.sav" & main'
echo ${idlcmd}
# Run IDL command
echo ${config} | idl -e "$idlcmd"
