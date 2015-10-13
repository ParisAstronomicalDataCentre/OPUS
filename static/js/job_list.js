(function($) {
    "use strict";

    var jobNames = ['ctbin'] //, 'astrocheck']
    var jobParameters = {
        evfile: "http://voplus.obspm.fr/cta/events.fits",
        emin: "0.1",
        emax: "100.0",
        enumbins: "20",
        nxpix: "200",
        nypix: "200",
        binsz: "0.02",
        coordsys: "CEL",
        xref: "85.25333404541016",
        yref: "22.01444435119629",
        proj: "TAN",
        "PHASE": "RUN",
    };

    function load_job_list() {
        var jobname = $('select[name=jobname]').val();
        // init UWS Manager
        uws_manager.initManager([jobname]);
        uws_manager.getJobList();
        if ( $( "#job_id" ).length ) {
            uws_manager.selectJob($( "#jobid" ).attr('value'));
        }
    }
    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        $('.selectpicker').selectpicker('deselectAll');
        // check if jobname is set in DOM
        var jobname = $('#jobname').attr('value');
        if (jobname) {
            $('select[name=jobname]').val(jobname);
            $('.selectpicker').selectpicker('refresh')
            load_job_list();
        };
        // Add events
        $('.selectpicker').on('change', function(){
            load_job_list();
        });
        $('#create_test_job').click( function() {
            var jobname = $('select[name=jobname]').val();
            uws_manager.createTestJob(jobname, jobParameters);
        });
        // Refresh button
        $('#refresh_list').click( function() {
            uws_manager.getJobList();
        });

    });
    
})(jQuery);
