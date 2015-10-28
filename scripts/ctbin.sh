#!/usr/bin/env bash
sleep 10
module load gammalib
source $GAMMALIB/bin/gammalib-init.sh
module load ctools
source $CTOOLS/bin/ctools-init.sh
echo $evfile
echo $outfile
ctbin evfile=$evfile outfile=$outfile prefix=cntmap_ ebinalg=LOG emin=0.1 emax=100.0 enumbins=$enumbins ebinfile=NONE usepnt=no nxpix=200 nypix=200 binsz=0.02 coordsys=CEL xref=83.63 yref=22.01 axisrot=0.0 proj=CAR chatter=2 clobber=yes debug=no mode=ql logfile=$logfile

#cp ${evfile##*/} evfile.fits
#echo "File $evfile copied to evfile.fits"
#cp ~/test/cntmap.fits .
#echo "File cntmap.fits created"
#cp ~/test/ctbin.log .
#echo "File ctbin.log created"
#echo "test fake result" > fake_result.txt
sleep 10