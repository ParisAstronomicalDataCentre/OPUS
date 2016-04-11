/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    function get_jobnames() {
        server_url = 'https://voparis-uws-test.obspm.fr/';  // Get from page variables
        // Get jobnames from server
        $.ajax({
            url : server_url + '/get_jobnames',
            async : true,
            cache : false,
            type : 'GET',
            dataType: "json",
            success : function(json) {
                for each (jn in jobnames['jobnames']) {
                    $('.selectpicker').append('<option>' + jn + '</option>')
                };
            $('.selectpicker').selectpicker('refresh');
            },
            error : function(xhr, status, exception) {
                console.log(exception);
            }
        });
    }

    function load_job_list() {
        var jobname = $('select[name=jobname]').val();
        var auth = $('#auth').attr('value');
        // init UWS Manager
        uws_manager.initManager([jobname], auth);
        uws_manager.getJobList();
        if ( $( "#job_id" ).length ) {
            uws_manager.selectJob($( "#jobid" ).attr('value'));
        }
        $('button.actions').removeAttr('disabled');
    };

    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        get_jobnames();
        $('.selectpicker').selectpicker('deselectAll');
        $('button.actions').attr('disabled', 'disabled');
        // check if jobname is set in DOM
        var jobname = $('#jobname').attr('value');
        if (jobname) {
            $('select[name=jobname]').val(jobname);
            $('.selectpicker').selectpicker('refresh');
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
