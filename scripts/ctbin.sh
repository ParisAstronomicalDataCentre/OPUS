#!/usr/bin/env bash

echo "Load modules"

module load gammalib
source $GAMMALIB/bin/gammalib-init.sh
module load ctools
source $CTOOLS/bin/ctools-init.sh

sleep 10

echo "Run ctbin"
ctbin \
    inobs=$evfile \
    outcube=$outfile \
    ebinalg=$ebinalg \
    emin=$emin \
    emax=$emax \
    enumbins=$enumbins \
    ebinfile=$ebinfile \
    usepnt=no \
    nxpix=$nxpix \
    nypix=$nypix \
    binsz=$binsz \
    coordsys=$coordsys \
    xref=$xref \
    yref=$yref \
    proj=$proj \
    chatter=$chatter \
    clobber=yes \
    debug=no \
    mode=$mode\
    logfile=$logfile

echo "Done"

