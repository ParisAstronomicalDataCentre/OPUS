/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var jobNames = ['ctbin'] //, 'astrocheck']

    function load_job_list() {
        var jobname = $('select[name=jobname]').val();
        // init UWS Manager
        uws_manager.initManager([jobname]);
        uws_manager.getJobList();
        if ( $( "#job_id" ).length ) {
            uws_manager.selectJob($( "#jobid" ).attr('value'));
        }
        $('button.actions').removeAttr('disabled');
    };

    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        $('.selectpicker').selectpicker('deselectAll');
        $('button.actions').attr('disabled', 'disabled');
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
        $('#refresh_list').click( function() {
            uws_manager.getJobList();
        });
        $('#create_test_job').click( function() {
            var jobname = $('select[name=jobname]').val();
            var formData = new FormData();
            formData.append('inobs', 'http://voplus.obspm.fr/cta/events.fits');
            //formData.append('PHASE', 'RUN');
            uws_manager.createTestJob(jobname, formData);
        });
        $('#create_new_job').click( function() {
            var jobname = $('select[name=jobname]').val();
            if (jobname) {
                window.location.href =  "/client/job_form/" + jobname;
            }
        });

    });
    
})(jQuery);