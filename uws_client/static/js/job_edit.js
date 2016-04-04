/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var jobname;
    var jobid;

    $(document).ready( function() {
    
        $('#form-buttons').remove();
        // Get jobname/jobid
        jobid = $('#jobid').attr('value');
        jobname = $('#jobname').attr('value');
        // Display job
        if (jobname && jobid) {
            uws_manager.initManager([jobname]);
            uws_manager.displaySingleJob(jobname, jobid);
        };
        // Add events
        $('#to_job_list').click( function() {
            window.location.href =  "/client/job_list?jobname=" + jobname;
        });
        
    });

})(jQuery);
