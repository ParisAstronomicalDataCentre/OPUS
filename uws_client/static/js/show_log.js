/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var log_url;
    var log_lines = [];
    var loaded_at = '';
    var refresh_timer = null;
    var REFRESH_PERIOD = 10000;  // in ms

    function escape_html(text) {
        return $('<div/>').text(text).html();
    }

    function level_class(line) {
        if (/\] (ERROR|CRITICAL) /.test(line)) { return 'log-error'; }
        if (/\] WARNING /.test(line)) { return 'log-warning'; }
        if (/\] DEBUG /.test(line)) { return 'log-debug'; }
        return '';
    }

    function show_log() {
        // Show the lines matching the filter, colored by level
        var filter = $('input[name=filter]').val().toLowerCase();
        var lines = log_lines;
        if (filter) {
            lines = lines.filter(function (line) { return line.toLowerCase().indexOf(filter) >= 0; });
        }
        var html = lines.map(function (line) {
            var cls = level_class(line);
            return cls ? '<span class="' + cls + '">' + escape_html(line) + '</span>' : escape_html(line);
        }).join('\n');
        var pre = $('#pre_log');
        pre.html(html);
        pre.scrollTop(pre.prop('scrollHeight'));  // most recent lines at the bottom
        var info = log_lines.length + ' lines';
        if (filter) { info = lines.length + ' of ' + info + ' matching "' + escape_html(filter) + '"'; }
        $('#log_info').html(info + ', loaded at ' + loaded_at);
    }

    function load_log() {
        $('#loading').show();
        $.ajax({
            url : log_url,
            cache : false,
            type : 'GET',
            dataType: 'text',
            data : {
                FILE: $('select[name=logfile]').val(),
                LINES: $('select[name=nlines]').val()
            },
            success : function(text) {
                $('#loading').hide();
                log_lines = text ? text.split('\n') : [];
                loaded_at = new Date().toLocaleTimeString();
                show_log();
            },
            error : function(xhr, status, exception) {
                $('#loading').hide();
                log_lines = [];
                $('#pre_log').empty();
                $('#log_info').empty();
                global.showMessage('Cannot load the log: ' + (exception || status) + ' (' + xhr.status + ')', 'danger');
            }
        });
    }

    function set_autorefresh() {
        if (refresh_timer) {
            clearInterval(refresh_timer);
            refresh_timer = null;
        }
        if ($('input[name=autorefresh]').is(':checked')) {
            refresh_timer = setInterval(load_log, REFRESH_PERIOD);
        }
    }

    // LOAD LOG AT STARTUP
    $(document).ready( function() {
        log_url = $('#log_url').attr('value');
        $('select[name=logfile], select[name=nlines]').on('change', load_log);
        $('input[name=filter]').on('input', show_log);
        $('input[name=autorefresh]').on('change', set_autorefresh);
        $('#refresh_log').click(load_log);
        load_log();
    });

})(jQuery);
