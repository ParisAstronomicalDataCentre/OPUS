/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var server_endpoint;
    var client_endpoint;

    var jobnames = [];

    function get_jobnames() {
        // Get jobnames from server
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl',
            cache : false,
            type : 'GET',
            dataType: "json",
            success : function(json) {
                $('#loading').hide();
                console.log(json['jobnames']);
                jobnames = json['jobnames'];
                // Fill select
                for (var jn in json['jobnames']) {
                    $('.selectpicker').append('<option value="' + json['jobnames'][jn] + '">' + json['jobnames'][jn] + '</option>')
                };
                $('.selectpicker').append('<option disabled>─────</option>');
                $('.selectpicker').append('<option>all</option>');
                $('.selectpicker').selectpicker('refresh');
                // Check if jobname is set in DOM
                var jobname = $('#jobname').attr('value');
                if (jobname) {
                    $('select[name=jobname]').val(jobname);
                    $('.selectpicker').selectpicker('refresh');
                    $('button.actions').removeAttr('disabled');
                    $('#edit_jdl').removeAttr('disabled');
                };
            },
            error : function(xhr, status, exception) {
                $('#loading').hide();
                console.log(exception);
                var jobname = $('#jobname').attr('value');
                if (jobname) {
                    $('.selectpicker').append('<option>' + jobname + '</option>');
                    $('select[name=jobname]').val(jobname);
                    $('.selectpicker').selectpicker('refresh');
                    $('button.actions').removeAttr('disabled');
                    $('#edit_jdl').removeAttr('disabled');
                };
            }
        });
    };

    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        get_jobnames();
        $('.selectpicker').selectpicker('deselectAll');
        $('button.actions').attr('disabled', 'disabled');
        $('#edit_jdl').attr("disabled", "disabled");
        // Add events
        $('.selectpicker').on('change', function(){
            var jobname = $('select[name=jobname]').val();
            if (jobname) {
                window.location.href =  client_endpoint + uws_client.client_endpoint_job_form + "/" + jobname;
            };
        });
        $('#create_new_job').click( function() {
            var jobname = $('select[name=jobname]').val();
            if (jobname) {
                window.location.href =  client_endpoint + uws_client.client_endpoint_job_form + "/" + jobname;
            };
        });

    });

})(jQuery);
