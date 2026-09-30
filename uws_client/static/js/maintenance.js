/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var client_endpoint;
    var report = null;
    var category_filter = null;  // show only the jobs of this category

    var CATEGORIES = {
        to_archive: {label: 'To archive', style: 'warning', title: 'Destruction time passed, the job will be archived'},
        phase: {label: 'Phase to update', style: 'warning', title: 'The job manager gives another phase'},
        to_delete: {label: 'To delete', style: 'danger', title: 'Destruction time passed, the job cannot be archived: it will be deleted (stopped if running)'},
        dates: {label: 'Inconsistent dates', style: 'danger', title: 'Dates not set or in the wrong order'},
        error: {label: 'Errors', style: 'danger', title: 'Error while checking the job'},
        archived: {label: 'Archived', style: 'outline-secondary', title: 'Jobs already archived'},
        ok: {label: 'No issue', style: 'success', title: 'Jobs without issue'}
    };
    var HIDDEN_BY_DEFAULT = ['ok', 'archived'];

    function escape_html(text) {
        return $('<div/>').text(text == null ? '' : text).html();
    }

    function to_apply(summary) {
        return summary.to_archive + summary.to_delete + summary.phase;
    }

    function show_summary() {
        var html = '';
        $.each(CATEGORIES, function (category, c) {
            var n = report.summary[category] || 0;
            var active = (category_filter == category) ? ' active' : '';
            html += '<button type="button" class="btn btn-' + c.style + ' btn-sm' + active + '" data-category="' + category
                + '" title="' + c.title + '"' + (n ? '' : ' disabled') + '>' + c.label + ' <span class="badge">' + n + '</span></button>';
        });
        if (category_filter) {
            html += '<button type="button" class="btn btn-link btn-sm" data-category="">Show all categories</button>';
        }
        $('#maintenance_summary').html(html);
        $('#maintenance_summary button').click(function () {
            var category = $(this).data('category');
            category_filter = (category && category != category_filter) ? category : null;
            show_report();
        });
    }

    function show_jobs() {
        var show_all = $('input[name=show_all]').is(':checked');
        var tbody = $('#maintenance_table tbody');
        tbody.empty();
        var shown = 0;
        $.each(report.jobs, function (i, job) {
            if (category_filter) {
                if (job.categories.indexOf(category_filter) < 0) { return; }
            } else if (!show_all && job.categories.every(function (c) { return HIDDEN_BY_DEFAULT.indexOf(c) >= 0; })) {
                return;
            }
            shown += 1;
            var job_url = client_endpoint + '/job_edit/' + encodeURIComponent(job.jobname) + '/' + encodeURIComponent(job.jobid);
            var notes = job.issues.map(function (s) { return '<div class="issues">' + escape_html(s) + '</div>'; })
                .concat(job.actions.map(function (s) { return '<div class="actions">' + escape_html(s) + '</div>'; }));
            if (!notes.length) { notes = ['<span class="text-muted">' + (job.categories.indexOf('archived') >= 0 ? 'archived' : 'ok') + '</span>']; }
            tbody.append('<tr>'
                + '<td>' + escape_html(job.jobname) + '</td>'
                + '<td><a href="' + job_url + '">' + escape_html(job.jobid) + '</a></td>'
                + '<td>' + escape_html(job.owner) + '</td>'
                + '<td>' + escape_html(job.phase) + '</td>'
                + '<td>' + escape_html(job.creation_time) + '</td>'
                + '<td>' + escape_html(job.start_time) + '</td>'
                + '<td>' + escape_html(job.end_time) + '</td>'
                + '<td>' + escape_html(job.destruction_time) + '</td>'
                + '<td>' + notes.join('') + '</td>'
                + '</tr>');
        });
        $('#maintenance_table').toggle(shown > 0);
        return shown;
    }

    function show_report() {
        show_summary();
        var shown = show_jobs();
        var n_apply = to_apply(report.summary);
        var info = report.jobs.length + ' jobs checked at ' + escape_html(report.date) + ', ' + shown + ' shown. ';
        if (report.apply) {
            info = '<b>Changes applied</b>: ' + info + 'Run a new check to see the current state.';
        } else if (n_apply) {
            info = '<b>Dry run</b>: ' + info + n_apply + ' change(s) to apply.';
        } else {
            info = '<b>Dry run</b>: ' + info + 'Nothing to apply.';
        }
        $('#maintenance_info').html(info);
        $('#button_apply').prop('disabled', report.apply || !n_apply);
    }

    function run_maintenance(apply) {
        $('#loading').show();
        $('#button_check, #button_apply').prop('disabled', true);
        $.ajax({
            url : server_url + '/maintenance',
            type : apply ? 'POST' : 'GET',
            cache : false,
            dataType : 'json',
            success : function (json) {
                $('#loading').hide();
                $('#button_check').prop('disabled', false);
                report = json;
                show_report();
                if (apply) { global.showMessage('Maintenance changes applied', 'success'); }
            },
            error : function (xhr, status, exception) {
                $('#loading').hide();
                $('#button_check').prop('disabled', false);
                global.showMessage('Maintenance failed (' + xhr.status + ': ' + (exception || status) + ')', 'danger');
            }
        });
    }

    $(document).ready(function () {
        server_url = $('#server_url').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        $('#button_check').click(function () { run_maintenance(false); });
        $('#button_apply').click(function () {
            var n = report ? to_apply(report.summary) : 0;
            var n_delete = report ? report.summary.to_delete : 0;
            var msg = 'Apply ' + n + ' change(s) (archive jobs, update phases'
                + (n_delete ? ', DELETE ' + n_delete + ' job(s) with their files' : '') + ')?\nAre you sure?';
            if (window.confirm(msg)) {
                run_maintenance(true);
            }
        });
        $('input[name=show_all]').change(function () { if (report) { show_report(); } });
    });

})(jQuery);
