/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var server_endpoint;
    var client_endpoint;

    var job_list_columns = [
        //'jobName',  // job.jobName
        'jobId',  // job.jobId
        'runId',  // job.runId
        'creationTime',
        'phase',
        'edit',
        //'details',
        //'results',
        'control',
        //'delete',
        //'ownerId',
    ];

    var jobnames = [];
    var ALL_JOBS = '_all_';  // value (and URL /jobs/_all_) of the list of all the jobs

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
                $('.selectpicker').append('<option value="' + ALL_JOBS + '">All jobs</option>');
                $('.selectpicker').selectpicker('refresh');
                // Check if jobname is set in DOM
                var jobname = $('#jobname').attr('value');
                if (jobname == 'all' && jobnames.indexOf('all') == -1) {
                    jobname = ALL_JOBS;  // previous URL of the list of all the jobs (/jobs/all)
                };
                if (jobname) {
                    $('select[name=jobname]').val(jobname);
                    $('.selectpicker').selectpicker('refresh');
                    load_job_list();
                };
            },
            error : function(xhr, status, exception) {
                $('#loading').hide();
                console.log(exception);
                // No list of job definitions: the server is not an OPUS server (e.g. a TAP server, set in the
                // Client Preferences): the job list is the one of the URL (/jobs/<name>), or the one of the
                // standard declared in the capabilities of the service (e.g. async for TAP)
                // No filter on the phases for such a server (list of the service as it is: some services return
                // nothing for several PHASE values)
                uws_client.setShowArchived(false);
                $('#show_archived').prop('checked', false).prop('disabled', true)
                    .parent().attr('title', 'Not available: jobs of an external UWS service');
                // The job list of such a server may only give the identifier and phase of the jobs: button to get
                // the details of each job
                $('#refresh_details').show();
                var show_job_list = function(jobname) {
                    if (jobname) {
                        $('.selectpicker').append('<option>' + jobname + '</option>');
                        $('select[name=jobname]').val(jobname);
                        $('.selectpicker').selectpicker('refresh');
                        load_job_list();
                    } else {
                        global.showMessage('No job list found on the server: it has no job definitions, and its '
                            + 'capabilities do not declare a known service (e.g. TAP). The name of a job list can '
                            + 'be given in the URL (/jobs/&lt;name&gt;).', 'warning');
                    };
                };
                var jobname = $('#jobname').attr('value');
                if (jobname || typeof uwsDescriptions === 'undefined') {
                    show_job_list(jobname);
                } else {
                    $('#loading').show();
                    uwsDescriptions.find(server_url + server_endpoint, null, function(found) {
                        $('#loading').hide();
                        show_job_list(found ? found.jobname : null);
                    });
                };
            }
        });
    };

    function load_job_list() {
        var jobname = $('select[name=jobname]').val();
        var col_sort = job_list_columns.indexOf('creationTime');
        $('button.actions').removeAttr('disabled');
        if (jobname == ALL_JOBS) {
            $('#loading').hide();
            // no job definition for the list of all the jobs
            $('#create_new_job').attr("disabled", "disabled");
            $('#edit_jdl').attr("disabled", "disabled");
            var cols = Array.from(job_list_columns);
            if (cols.indexOf('jobName') == -1) {
                cols.splice(0, 0, "jobName");
            };
            if (jobnames.length > 0) {
                uws_client.initClient(server_url, server_endpoint, client_endpoint, jobnames, cols);
            };
        } else {
            uws_client.initClient(server_url, server_endpoint, client_endpoint, [jobname], job_list_columns);
        };
        // init UWS Client
        // write new url in browser bar
        history.pushState({ jobname: jobname }, '', client_endpoint + uws_client.client_endpoint_jobs + "/" + jobname);
        // Prepare job list
        uws_client.getJobList();
        //if ( $( "#job_id" ).length ) {
        //    uws_client.selectJob($( "#jobid" ).attr('value'));
        //}
    };

    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        get_jobnames();
        $('.selectpicker').selectpicker('deselectAll');
        $('button.actions').attr('disabled', 'disabled');
        // Archived jobs listed or not (choice kept in the browser)
        var show_archived = false;
        try {
            show_archived = (window.localStorage.getItem('opus_show_archived') == 'true');
        } catch (e) {}
        $('#show_archived').prop('checked', show_archived);
        uws_client.setShowArchived(show_archived);
        $('#show_archived').on('change', function(){
            var show = $(this).prop('checked');
            try {
                window.localStorage.setItem('opus_show_archived', show ? 'true' : 'false');
            } catch (e) {}
            uws_client.setShowArchived(show);
            if ($('select[name=jobname]').val()) {
                uws_client.getJobList();
            };
        });
        // Add events
        $('.selectpicker').on('change', function(){
            load_job_list();
        });
        $('#refresh_list').click( function() {
            uws_client.getJobList();
        });
        // Details of each job of the list (run id, creation time, phase), then sorted by creation time
        $('#refresh_details').click( function() {
            var button = $(this), label = button.find('.refresh-details-label');
            button.attr('disabled', 'disabled');
            uws_client.getJobListDetails(function(done, total, finished) {
                if (finished) {
                    label.text('Refresh with details');
                    button.removeAttr('disabled');
                } else {
                    label.text('Details ' + done + ' / ' + total);
                }
            });
        });
        $('#edit_jdl').click( function() {
            var jobname = $('select[name=jobname]').val();
            if (jobname) {
                console.log(uws_client.client_endpoint_job_form);
                console.log(uws_client.client_endpoint_job_definition);
                window.location.href =  client_endpoint + uws_client.client_endpoint_job_definition + "/" + jobname;
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
