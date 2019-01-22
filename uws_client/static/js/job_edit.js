/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var server_endpoint;
    var client_endpoint;
    var jobname;
    var jobid;

    $(document).ready( function() {
    
        $('#form-buttons').remove();
        // Get jobname/jobid
        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        jobname = $('#jobname').attr('value');
        jobid = $('#jobid').attr('value');
        // Display job
        if (jobname && jobid) {
            uws_client.initClient(server_url, server_endpoint, client_endpoint, [jobname]);
            uws_client.displaySingleJob(jobname, jobid);
        };
        // Rerun job button
        $('#rerun_job').click( function() {
            // Collect job params
            var all_params = JSON.parse($('#all_params').attr('value'));
            var query_string = $.param(all_params);
            location.href = client_endpoint + uws_client.client_endpoint_job_form + "/" + jobname + '?' + query_string;
        })
    });

})(jQuery);
