#!/usr/bin/perl -w

use lib "/home/vouws/uws";

use constant BASE_WORKING_PATH => "/scratch/vouws/";
use constant BASE_RESULTS_PATH => "/poubelle/vouws/uwsdata/";
#use constant BASE_RESULTS_PATH => "www@voparis-uws.obspm.fr:/share/web/data/";

use Uws;

my $uws = Uws->new(BASE_WORKING_PATH, BASE_RESULTS_PATH);
$uws->init();

$wp = $uws->{_working_path};

my $evfile_url = $ARGV[0];
my $enumbins = $ARGV[1];

my $evfile = $wp . '/evfile.fits';
my $outfile = $wp . '/outfile.fits';
my $ctbin_log = $wp . '/ctbin.log';
my $ctbin_sh = $wp . '/ctbin.sh';

# get eventlist from url
$cmd = "wget '$evfile_url' -O $evfile";
$uws->execute($cmd);

# script to set the environment and run the script
open (MYFILE, ">$ctbin_sh") || die ("Cannot create ctbin.sh");
print MYFILE "#!/bin/bash -l \n";
print MYFILE "module load gammalib \n";
print MYFILE "source \$GAMMALIB/bin/gammalib-init.sh \n";
print MYFILE "module load ctools \n";
print MYFILE "source \$CTOOLS/bin/ctools-init.sh \n";
print MYFILE "ctbin evfile=$evfile outfile=$outfile prefix=cntmap_ ebinalg=LOG emin=0.1 emax=100.0 enumbins=$enumbins ebinfile=NONE usepnt=no nxpix=200 nypix=200 binsz=0.02 coordsys=CEL xref=83.63 yref=22.01 axisrot=0.0 proj=CAR chatter=2 clobber=yes debug=no mode=ql logfile=$ctbin_log";
#print MYFILE "fits2png.py $outfile";
close(MYFILE);
system("chmod u+x $ctbin_sh");

# wait 1min to fake a longer processing
sleep(20);

# run the job
$cmd = $ctbin_sh;
$uws->execute($cmd);

@out = ("outfile.fits", "ctbin.log");
$uws->end(@out);

