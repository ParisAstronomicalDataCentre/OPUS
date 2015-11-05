#!/usr/bin/env bash
sleep 10
module load gammalib
source $GAMMALIB/bin/gammalib-init.sh
module load ctools
source $CTOOLS/bin/ctools-init.sh
ctbin \
    evfile=$evfile \
    outfile=$outfile \
    prefix=$prefix \
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
    axisrot=$axisrot \
    proj=$proj \
    chatter=$chatter \
    clobber=yes \
    debug=no \
    mode=$mode \
    logfile=$logfile

#cp ${evfile##*/} evfile.fits
#echo "File $evfile copied to evfile.fits"
#cp ~/test/cntmap.fits .
#echo "File cntmap.fits created"
#cp ~/test/ctbin.log .
#echo "File ctbin.log created"
#echo "test fake result" > fake_result.txt
sleep 10