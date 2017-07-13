/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var endpoint;
    var jobname;
    var jobid;

    $(document).ready( function() {
    
        $('#form-buttons').remove();
        // Get jobname/jobid
        server_url = $('#server_url').attr('value');
        endpoint = $('#endpoint').attr('value');
        jobname = $('#jobname').attr('value');
        jobid = $('#jobid').attr('value');
        var auth = $('#auth').attr('value');
        // Display job
        if (jobname && jobid) {
            uws_client.initManager(server_url, [jobname], auth);
            uws_client.displaySingleJob(jobname, jobid);
        };
    });

})(jQuery);
