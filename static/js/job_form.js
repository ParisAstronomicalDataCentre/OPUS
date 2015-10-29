(function($) {
    "use strict";

    var jobName = 'ctbin';

    $(document).ready( function() {
        
        // Look at URL to set jobName
        jobName = $('#jobname').attr('value');
        uws_manager.initManager([jobName]);
        uws_manager.displayParamForm(jobName);

        // catch the form's submit event to validate form
        $('#job_params').submit(function(event) {
            event.preventDefault();
            var formData = new FormData($('#job_params')[0]);
            formData.append('PHASE', 'RUN');
            uws_manager.createJob(jobName, formData);
        });

        $('#to_job_list').click( function() {
            window.location.href =  "/client/job_list?jobname=" + jobName;
        });

    });
        
})(jQuery);
