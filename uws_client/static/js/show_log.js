/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var server_endpoint;
    var client_endpoint;
    var logfile;
    var nlines;

    function load_log() {
        var nlines = $('select[name=nlines]').val();
        var col_sort = job_list_columns.indexOf('creationTime');

    };

    // LOAD JOB LIST AT STARTUP
    $(document).ready( function() {

        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        get_jobnames();
        $('.selectpicker').selectpicker();
        // Add events
        $('.selectpicker').on('change', function(){
            load_log();
        });
        $('#refresh_list').click( function() {
            load_log();
        });

    });

})(jQuery);
