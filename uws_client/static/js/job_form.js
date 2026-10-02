/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var server_endpoint;
    var client_endpoint;
    var jobname = 'copy';

    $(document).ready( function() {
        
        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        jobname = $('#jobname').attr('value');
        var params = $('#init_params').attr('value');
        var init_params = JSON.parse(params);
        uws_client.initClient(server_url, server_endpoint, client_endpoint, [jobname]);
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
            if (uws_client.isExternal(jobname)) {
                // external UWS service (e.g. TAP server): the parameters left empty are not sent (defaults of the
                // service), nor the fields used by OPUS only
                Array.from(formData.keys()).forEach(function(key) {
                    if (formData.get(key) === '' || key == 'control_parameters') {
                        formData.delete(key);
                    }
                });
            }
            formData.append('PHASE', 'RUN');
            //var anim_icon = '<span class="bi bi-arrow-clockwise spin"></span>&nbsp;';
            //$('button[type=submit]').html(anim_icon);
            uws_client.createJob(jobname, formData);
            global.showMessage('Job submitted to server, waiting for response...', 'info');
        });
    });
        
})(jQuery);
