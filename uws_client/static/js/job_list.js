/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var client_url;

    function get_jobnames() {
        // Get jobnames from server
        $.ajax({
            url : server_url + '/jdl',
            cache : false,
            type : 'GET',
            dataType: "json",
            success : function(json) {
                console.log(json['jobnames']);
                // Fill select
                for (var jn in json['jobnames']) {
                    $('.selectpicker').append('<option>' + json['jobnames'][jn] + '</option>')
                };
                $('.selectpicker').selectpicker('refresh');
                // Check if jobname is set in DOM
                var jobname = $('#jobname').attr('value');
                if (jobname) {
                    $('select[name=jobname]').val(jobname);
                    $('.selectpicker').selectpicker('refresh');
                    load_job_list();
                };
            },
            error : function(xhr, status, exception) {
                console.log(exception);
            }
        });
    }

    function load_job_list() {
        var jobname = $('select[name=jobname]').val();
        // init UWS Client
        uws_client.initClient(client_url, server_url, [jobname]);
        // write new url in browser bar
        history.pushState({ jobname: jobname }, '', uws_client.client_url + uws_client.client_url_jobs + "/" + jobname);
        // Prepare job list
        uws_client.getJobList();
        if ( $( "#job_id" ).length ) {
            uws_client.selectJob($( "#jobid" ).attr('value'));
        }
        $('button.actions').removeAttr('disabled');
    };

    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        server_url = $('#server_url').attr('value');
        client_url = $('#client_url').attr('value');
        get_jobnames();
        $('.selectpicker').selectpicker('deselectAll');
        $('button.actions').attr('disabled', 'disabled');
        // Add events
        $('.selectpicker').on('change', function(){
            load_job_list();
        });
        $('#refresh_list').click( function() {
            uws_client.getJobList();
        });
        $('#create_test_job').click( function() {
            var jobname = $('select[name=jobname]').val();
            var formData = new FormData();
            //formData.append('inobs', 'http://voplus.obspm.fr/cta/events.fits');
            //formData.append('PHASE', 'RUN');
            uws_client.createTestJob(jobname, formData);
        });
        $('#create_new_job').click( function() {
            var jobname = $('select[name=jobname]').val();
            if (jobname) {
                window.location.href =  client_url + uws_client.client_url_job_form + "/" + jobname;
            }
        });

    });
    
})(jQuery);
