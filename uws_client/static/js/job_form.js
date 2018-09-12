/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var client_url;
    var jobname = 'copy';

    $(document).ready( function() {
        
        server_url = $('#server_url').attr('value');
        client_url = $('#client_url').attr('value');
        jobname = $('#jobname').attr('value');
        var params = $('#init_params').attr('value');
        var init_params = JSON.parse(params);
        uws_client.initClient(client_url, server_url, [jobname]);
        uws_client.displayParamForm(jobname, init_params);

        // catch the form's submit event to validate form
        $('#job_params').submit(function(event) {
            event.preventDefault();
            var formData = new FormData($('#job_params')[0]);
//            $('input[type=file]').each( function() {
//                console.log('Adding: ' + $(this).attr('name'));
//                console.log($(this)[0].files[0]);
//                formData.append($(this).attr('name'), $(this)[0].files[0]);
//            });
            formData.append('PHASE', 'RUN');
            uws_client.createJob(jobname, formData);
        });
    });
        
})(jQuery);
