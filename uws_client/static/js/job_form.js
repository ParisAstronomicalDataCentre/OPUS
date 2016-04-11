/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var jobname = 'copy';

    $(document).ready( function() {
        
        server_url = $('#server_url').attr('value');
        jobname = $('#jobname').attr('value');
        var auth = $('#auth').attr('value');
        uws_manager.initManager(server_url, [jobname], auth);
        uws_manager.displayParamForm(jobname);

        // catch the form's submit event to validate form
        $('#job_params').submit(function(event) {
            event.preventDefault();
            var formData = new FormData($('#job_params')[0]);
            formData.append('PHASE', 'RUN');
            uws_manager.createJob(jobname, formData);
        });

        $('#to_job_list').click( function() {
            window.location.href =  "/client/job_list?jobname=" + jobname;
        });

    });
        
})(jQuery);
