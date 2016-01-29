#!/usr/bin/env bash
### Load needed modules
# ROOT
module load root/5.34.34
source /usr/local/root_v5.34.34/bin/thisroot.sh
# Environment variables
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/obs/vouws/scripts/gammastart/lib
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:/obs/vouws/scripts/gammastart/lib
# ROOT options (batch and quit)
rootopt="-q"

### JLK, variables to define in the UWS environment for configuration file:
gammastart_dir=/obs/vouws/scripts/gammastart/
listdir=${gammastart_dir}/test/
outdir=./
# access to data
datadir=${gammastart_dir}/test/data/
export HESSCONFIG=${gammastart_dir}/test/IRF/
#cp $data .

### Copy needed files
# rootlogon to be loaded by start (same dir as root -l)
rootlogon=${gammastart_dir}/rootlogon.C
cp $rootlogon .
# script to be launch
script=${gammastart_dir}/start/scripts/startfit.C
cp $script .

echo "CHECK"
echo "`ls -l /etc/root/gdb-backtrace.sh`"
echo "`ls -l $ROOTSYS/etc/plugins/`"

### Generate configuration file
export configfile
cat > $configfile << EOF
#########################################                                                                               
###        Configuration file         ###                                                                               
###     A comment begins by "###"     ###                                                                               
#########################################   
[USER]
### Use input file list instead of run list (default is 0).                                                             
### This can be useful for MC studies.                                                                                  
UserUseInputFileList 0
### Run lists folder adress (absolute path)                                                                             
UserRunListsFolderAdress ${listdir}
### Run list file name (will be automatically completed by .list)                                                       
UserRunListFileBaseName ${runlist}
### Folder in which outputs are written (absolute path)                                                                 
### if empty, nothing is saved                                                                                          
UserOutputFolderName ${outdir}
### Output will be saved as UserOutputFolderName/UserOutputRootFileName.root                                            
UserOutputRootFileName ${fitresult}

[Data]
### Indivual runs root files folder adress (absolute path)                                                              
### (runs produced by the analysis and used as input for the spectrum)                                                  
UserRootFilesFolderAddress ${datadir}
### Set a cos(zenith) range max value : if the run cos(zen) distrib                                                     
### is larger than this value, the two zen bands will be used                                                           
UserMaxCosZenBinWidth 1.
### Set zenith max (compare to each zen band mean value. Skip part of run if necessary)                                 
UserZenithMax 70.
### Set offset max (cut used for select runs)                                                                           
UserOffsetMax 2.4
### Set minimal time (seconds) to consider a zen and offset band                                                        
UserTmin 200.

### Use MJD windows for spectrum                                                                                        
### range have to be separated by a coma                                                                                
### Add an arbitrary number of lines such as:                                                                           
###UserMJDwindow 53944.12345,53944.23223                                                                                

[Analysis]
### A label for the user analysis configuration (azimuth, cuts, analysis type)                                          
### this is used for output names and also for collection area and resolution access                                    
UserAnalysisConfig ${anaconfig}
### Config type (unused at present: use preferably UserMcProductionName)                                                
UserAnalysisConfigType default
### Force area & resol analysis config (usefull for extended sources)                                                   
#UserForceAreaAnalysisConfig elm_south_hyb_Prod15_2
### Minimal effective area used to determine treshold
UserAreaMin 4.
### Set energy range MIN value (TeV)                                                                                
UserERangeMin ${emin}
### Set energy range MAX value                                                                                      
UserERangeMax ${emax}
### Set energy number of bins                                                                                       
UserERangeBinsNumber ${nebin}
### Option to compute contours                                                                                          
### choice are :                                                                                                        
### 0 no contours                                                                                                       
### 1 contours for two first parameters of all hypothesis                                                               
### 2 all contours are computed for all hypothesis (can be very long)                                                   
UserComputeContours ${optcontour}
### Number of points for countours                                                                                      
UserContoursNumberOfPoints ${optcontour_npoints}
### Option to compute contours                                                                                          
### choice are :                                                                                                        
### 0 no scans                                                                                                          
### 1 scans are computed for all hypothesis and all parameters                                                          
UserComputeScanLikelihood 0
### Option for minimization "intensity"                                                                                 
### choice are :                                                                                                        
### 0 minimization is done for hypothesis                                                                               
### 1 minimization is done for hypothesis + minos errors                                                                
### 2 minimization is done for hypothesis, integrated flux hypothesis and energy flux hypothesis                        
### 3 minimization is done for hypothesis + minos errors, integrated flux hypothesis and energy flux hypothesis         
UserMinimizationLevel ${optminimisationlevel}
### If 1 comparison by minimization will be done for all hypothesis                                                     
UserHypothesisComparison 0

[LightCurve]
### Time cutting type                                                                                                   
### 0 no LightCurve                                                                                                     
### 1 Run by run                                                                                                        
### 2 Minute by minute                                                                                                  
### 3 Hour by hour (1h)                                                                                                 
### 4 Night by night (12h)                                                                                              
### 5 Day by day (24h)                                                                                                  
### 6 Week by week (7x24h)                                                                                              
### 7 Month by month (30x24h)                                                                                           
### 8 Year by year (365.25 days)                                                                                        
### 9 GivenTimeInterval (specify the value of UserLightCurveTimeInterval in seconds)                                    
### 10 UserTimeIntervals (specify the values of UserLightCurveUserTimeIntervals in MJD)                                 
### 11 PeriodByPeriod (Full moon from full moon)                                                                        
### Add an arbitrary number of lines such as:                                                                           
UserLightCurveTimeCuttingType ${optlc}
### Time range used for light curve in MJD time                                                                         
### Interval have to be separated by a coma                                                                             
UserLightCurveTimeRange 0,90000
### Integrated flux energy range (TeV)                                                                                  
UserLightCurveIntegratedFluxEnergyRange ${opteminhyp},${optemaxhyp}
### Time interval used for light curve in MJD time for time cutting type GivenTimeInterval                              
### Interval have to be set in SECONDS!                                                                                 
UserLightCurveTimeInterval 60.
### User time intervals in MJD for time cutting type UserTimeIntervals                                                  
### Add an arbitrary number of lines such as:                                                                           
### UserLightCurveUserTimeIntervals 55000,55500
### Light curves plot time axis units                                                                                   
### 0 MJD                                                                                                               
### 1 year and month #splitline{Jul}{2012}                                                                              
### 2 Year, month and day (e.g 23/03/12)                                                                                
### 3 Hour, minute and second (23:12:06)                                                                                
UserLightCurveTimeAxisUnits 0
### Light curves plot errors handling                                                                                   
### 0 Gaussian                                                                                                          
### 1 Rolke                                                                                                             
### Add an arbitrary number of lines like:                                                                                     
UserLightCurveErrorsHandling 1
[MC]
### MC production used to determine the threshold (will be completed automatically by _eff##)                           
UserMcProductionName gFixedEnergy_paris_0-8-8-8_CamOptimal_hwtrig
### For MC runs                                                                                                         
UserIsMc 0

[Hypothesis]
### It is possible to minimize a set of hypothesis. You can add hypothesis as much                                      
### as you want. For example :                                                                                          
### UserAddHypothesis 1                                                                                                 
### UserAddHypothesis 4                                                                                                 
### will add a PowerLaw and a BrokenPowerLaw. Hypothesis are defined by :                                               
### 1 = PowerLaw                                                                                                        
### 2 = ExpoCutOffPowerLaw                                                                                              
### 3 = LogParabolic                                                                                                    
### 4 = BrokenPowerLaw                                                                                                  
### 5 = SuperExpoCutOffPowerLaw                                                                                         
### 6 = SmoothBrokenPowerLaw                                                                                            
### Add an arbitrary number of lines such as:                                                                           
UserAddHypothesis ${opthyp}

### To define the reference energy (TeV)
UserEref ${opterefhyp}
### To define the integration range for integrated hypothesis                                                           
### range have to be separated by a coma                                                                                
UserHypothesisIntegrationEnergyRange ${opteminhyp},${optemaxhyp}

[Plots]
### Name of the source to add on the main plot (PlotFactory::UserFriendly)                                              
### If none, no name will be printed on plots (for all plotstyles).                                                     
UserSourceName ${optsrcname}
### If 0 you won't have spectrum's plot and if 1 tou will                                                               
UserDrawPlots 1
### If 0 Default : same as UserFriendly without bins in spectrum                                                        
### If 1 UserFriendly : The cherry on the cake                                                                          
### If 2 Paper : same as UserFriendly without TPaveText, source name and bins in spectrum                               
UserPlotStyle 1
### Define the butterfly on the main plot                                                                               
### You have the choice with :                                                                                          
### 0 no butterfly is drawn                                                                                             
### 1 linear butterfly (covariance of flux) is drawn                                                                    
### 2 logarithm butterfly (covariance of log flux e.g. Fermi) is drawn                                                  
### 3 contours (contours have to be computed, works only for PWL!!) is drawn                                            
### 4 Caustic (contours have to be computed, works only for PWL!!) is drawn                                             
### Add an arbitrary number of lines such as:                                                                           
UserButterfly ${optbutterfly}
### Set the minimum significance each used energy bin must have                                                         
### If 0, no rebinning will be done                                                                                     
### Add an arbitrary number of lines such as:                                                                           
UserHypothesisRebin ${optrebin}
### If 1 a line representing the best fitted parameters will be drawn of the main spectrum                              
UserFitResultsDrawing 0

EOF

### End of configuration file

root.exe $rootopt rootlogon.C "startfit.C+(\"$configfile\")"
mv ${fitresult}.root ${fitresult}


### End of job
