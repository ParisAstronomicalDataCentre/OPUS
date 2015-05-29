package Uws;
use vars qw(@ISA @EXPORT);
use Exporter;
@ISA = qw(Exporter);
@EXPORT = qw(new init end);

use strict;

my $wp;
my $rp;

sub new {
   my ($class, $base_working_path, $base_results_path) = @_;
   if($ENV{SLURM_JOBID}) {
      my $this = {
         _working_path  => $base_working_path . $ENV{SLURM_JOBID},
         _results_path  => $base_results_path . $ENV{SLURM_JOBID},
      };
      $wp = $base_working_path . $ENV{SLURM_JOBID};
      $rp = $base_results_path . $ENV{SLURM_JOBID};

      bless($this, $class);
      return $this;
   } else {
      die "run out of SLURM scope (\$ENV{SLURM_JOBID} not defined)";
   }
}

sub init {
   my ($this) = @_;

   # prepare the directory where to save the results and log 
   my $cmd0 = "mkdir -p $this->{_results_path}";
   system($cmd0);
   print STDOUT $cmd0 . "\n";

   # prepare the directory where to save log
   my $cmd1 = "mkdir -p $this->{_results_path}/log";
   system($cmd1);
   print STDOUT $cmd1 . "\n";

   # prepare the working directory and chdir to it
   my $cmd2 = "mkdir -p $this->{_working_path}";
   system($cmd2);
   print STDOUT $cmd2 . "\n";
   chdir($this->{_working_path});

   $SIG{__DIE__} = \&errorhandler;
}

sub end {
   my ($this, @res) = @_;

   # save the results to right directory
   my $cmd0 = "mkdir -p $this->{_results_path}/results";
   system($cmd0);
   print STDOUT $cmd0 . "\n";
   
   my $f;
   foreach $f (@res) {
      my $cmd = "cp -r $this->{_working_path}/$f $this->{_results_path}/results/.";
      system($cmd);
      print STDOUT $cmd . "\n";
   }
   
   # delete the working directory
   my $cmd2 = "rm -rf $this->{_working_path}";
   system($cmd2);
   print STDOUT $cmd2 . "\n";

   # mark this job done
   my $cmd3 = "touch $this->{_results_path}/done";
   system($cmd3);
   print STDOUT $cmd3 . "\n";
}

sub errorhandler {
   my ($this) = @_;
   
   # delete the working directory
   my $cmd0 = "rm -rf " . $wp;
   system($cmd0);
   print STDOUT $cmd0 . "\n";

   # mark this job error
   my $cmd1 = "touch $rp/error";
   system($cmd1);
   print STDOUT $cmd1 . "\n";
   
   exit 1;
}

sub execute {
   my ($this, $cmd) = @_;

   # execute the given command
   system($cmd);

   #check for failure
   if($? != 0) {
      print STDERR $cmd . " FAILED\n";
      die "";
   } else {
      print STDOUT $cmd . "\n";
   }
}

1;
