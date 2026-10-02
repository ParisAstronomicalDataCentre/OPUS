/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var client_endpoint;
    var report = null;
    var shown_categories = {};  // categories whose jobs are listed (none after a check)

    var CATEGORIES = {
        to_archive: {label: 'To archive', style: 'warning',
                     title: 'Destruction time passed, job finished: it will be archived (results and upload files will be removed)',
                     title_delete: 'Destruction time passed, job finished: it will be deleted'},
        phase: {label: 'Phase to update', style: 'warning', title: 'The job manager gives another phase'},
        to_delete: {label: 'To delete', style: 'danger',
                    title: 'Destruction time passed, job not finished: it will be deleted'},
        archived_files: {label: 'Archived, files to remove', style: 'warning',
                         title: 'Job already archived, but its result files are still on the server: they will be removed'},
        dates: {label: 'Inconsistent dates', style: 'danger', title: 'Dates not set or in the wrong order'},
        error: {label: 'Errors', style: 'danger', title: 'Error while checking the job'},
        archived: {label: 'Archived', style: 'secondary', title: 'Jobs already archived, without result files'},
        ok: {label: 'No issue', style: 'success', title: 'Jobs without issue'}
    };
    // Changes to apply, selected in the summary (categories with a change), and action for the jobs to archive
    var apply_select = {to_archive: true, phase: true, to_delete: true, archived_files: true};
    var archive_action = 'archive';  // or 'delete'

    function escape_html(text) {
        return $('<div/>').text(text == null ? '' : text).html();
    }

    // Number of changes selected
    function to_apply(summary) {
        var n = 0;
        $.each(apply_select, function (category, selected) {
            if (selected) { n += summary[category] || 0; }
        });
        return n;
    }
    function selected_categories(summary) {
        return Object.keys(apply_select).filter(function (c) { return apply_select[c] && summary[c]; });
    }

    // Cell of the summary to select a change to apply: checkbox, and for the jobs to archive, archive or delete
    function apply_cell(category, n) {
        if (!(category in apply_select)) {
            return '';
        }
        var disabled = (!n || report.apply) ? ' disabled' : '';
        // (checkbox and list centered vertically)
        var html = '<div class="d-flex align-items-center gap-2">'
            + '<input type="checkbox" class="form-check-input mt-0 apply-select" data-category="' + category + '"'
            + ' title="Apply this change"' + ((apply_select[category] && n) ? ' checked' : '') + disabled + '/>';
        if (category == 'to_archive') {
            html += '<select class="form-select form-select-sm w-auto archive-action"'
                + ' title="What to do with the jobs after their destruction time: archive (result files deleted, '
                + 'description, logs and provenance kept), or delete the jobs"' + disabled + '>'
                + '<option value="archive"' + (archive_action == 'archive' ? ' selected' : '') + '>Archive</option>'
                + '<option value="delete"' + (archive_action == 'delete' ? ' selected' : '') + '>Delete</option>'
                + '</select>';
        }
        return html + '</div>';
    }

    // Categories with jobs (their jobs can be listed)
    function available_categories() {
        return Object.keys(CATEGORIES).filter(function (c) { return report.summary[c]; });
    }

    // Summary of the check: table of the categories, with the number of jobs, the changes to apply, and a button
    // to list the jobs of the category in the table of the jobs (several categories can be listed)
    function show_summary() {
        var available = available_categories();
        var all_shown = available.length > 0 && available.every(function (c) { return shown_categories[c]; });
        var html = '<table class="table table-bordered table-sm">'
            + '<thead><tr><th>Category</th><th class="text-end">Jobs</th><th>Description</th>'
            + '<th title="Changes applied by Apply changes">Apply</th>'
            + '<th><button type="button" id="show_all" class="btn btn-outline-secondary btn-sm' + (all_shown ? ' active' : '') + '"'
            + ' title="List the jobs of all the categories below, or none"' + (available.length ? '' : ' disabled') + '>'
            + (all_shown ? 'Hide all' : 'Show all') + '</button></th>'
            + '</tr></thead><tbody>';
        $.each(CATEGORIES, function (category, c) {
            var n = report.summary[category] || 0;
            var active = !!(n && shown_categories[category]);
            html += '<tr' + (active ? ' class="table-active"' : '') + '>'
                + '<td><span class="badge text-bg-' + (n ? c.style : 'light') + '">' + c.label + '</span></td>'
                + '<td class="text-end' + (n ? ' fw-bold' : ' text-muted') + '">' + n + '</td>'
                + '<td class="text-muted">' + ((archive_action == 'delete' && c.title_delete) || c.title) + '</td>'
                + '<td>' + apply_cell(category, n) + '</td>'
                + '<td><button type="button" class="btn btn-outline-secondary btn-sm show-jobs' + (active ? ' active' : '')
                + '" data-category="' + category + '" title="List the jobs of this category below, or not"' + (n ? '' : ' disabled') + '>'
                + (active ? 'Shown' : 'Show') + '</button></td>'
                + '</tr>';
        });
        html += '</tbody></table>';
        $('#maintenance_summary').html(html);
        $('#show_all').click(function () {
            shown_categories = {};
            if (!all_shown) {
                available.forEach(function (c) { shown_categories[c] = true; });
            }
            show_report();
        });
        // changes to apply
        $('#maintenance_summary input.apply-select').change(function () {
            apply_select[$(this).data('category')] = $(this).is(':checked');
            show_info();
        });
        $('#maintenance_summary select.archive-action').change(function () {
            archive_action = $(this).val();
            run_maintenance(false);  // new check: the changes listed for the jobs follow the choice
        });
        $('#maintenance_summary button.show-jobs').click(function () {
            var category = $(this).data('category');
            shown_categories[category] = !shown_categories[category];
            show_report();
        });
    }

    function show_jobs() {
        var tbody = $('#maintenance_table tbody');
        tbody.empty();
        var shown = 0;
        $.each(report.jobs, function (i, job) {
            // jobs of the categories shown (none by default)
            if (!job.categories.some(function (c) { return shown_categories[c]; })) {
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
        $('#maintenance_jobs').toggle(shown > 0);
        var labels = Object.keys(CATEGORIES)
            .filter(function (c) { return shown_categories[c] && report.summary[c]; })
            .map(function (c) { return CATEGORIES[c].label.toLowerCase(); });
        $('#maintenance_jobs_title').text(shown + ' job(s) shown: ' + labels.join(', '));
        return shown;
    }

    var last_applied = '';  // what was applied by the last Apply changes (a new check is run after it)
    function show_info() {
        var n_apply = to_apply(report.summary);
        var info = report.jobs.length + ' jobs checked at ' + escape_html(report.date) + '. ';
        if (report.apply) {
            var applied = (report.applied || []).map(function (c) { return CATEGORIES[c].label.toLowerCase(); });
            info = '<b>Changes applied</b> (' + (applied.join(', ') || 'none') + '): ' + info
                + 'Run a new check to see the current state.';
        } else if (n_apply) {
            info = '<b>Dry run</b>: ' + info + n_apply + ' change(s) selected to apply.';
        } else {
            info = '<b>Dry run</b>: ' + info + 'Nothing to apply.';
        }
        if (last_applied && !report.apply) {
            info = '<b>' + escape_html(last_applied) + '</b><br/>' + info;
        }
        $('#maintenance_info').html(info);
        $('#button_apply').prop('disabled', report.apply || !n_apply);
    }

    function show_report() {
        show_summary();
        show_jobs();
        show_info();
    }

    function run_maintenance(apply) {
        $('#loading').show();
        $('#button_check, #button_apply').prop('disabled', true);
        // changes to apply (selected in the summary), and action for the jobs to archive
        var data = {ARCHIVE_ACTION: archive_action};
        if (apply) {
            var selected = selected_categories(report.summary);
            data.APPLY = selected.length ? selected : ['none'];
        }
        $.ajax({
            url : server_url + '/maintenance',
            type : apply ? 'POST' : 'GET',
            data : data,
            traditional : true,  // APPLY=a&APPLY=b
            cache : false,
            dataType : 'json',
            success : function (json) {
                $('#loading').hide();
                $('#button_check').prop('disabled', false);
                report = json;
                if (apply) {
                    // what was applied (number of jobs by change), then a new check to show the current state
                    var changes = (json.applied || []).filter(function (c) { return json.summary[c]; })
                        .map(function (c) { return CATEGORIES[c].label.toLowerCase() + ': ' + json.summary[c]; });
                    last_applied = 'Changes applied at ' + json.date + ' (' + (changes.join(', ') || 'none')
                        + (json.summary.error ? ', errors: ' + json.summary.error : '') + ').';
                    global.showMessage('Maintenance changes applied', json.summary.error ? 'warning' : 'success');
                    run_maintenance(false);
                    return;
                }
                show_report();
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
        $('#button_check').click(function () {
            shown_categories = {};  // no job listed after a check
            last_applied = '';
            run_maintenance(false);
        });
        $('#button_apply').click(function () {
            if (!report) { return; }
            var summary = report.summary;
            var changes = selected_categories(summary).map(function (category) {
                var n = summary[category];
                if (category == 'to_archive') {
                    return (archive_action == 'delete')
                        ? '- DELETE ' + n + ' job(s) after their destruction time, with their files (instead of archiving them)'
                        : '- archive ' + n + ' job(s) (result files deleted)';
                }
                if (category == 'to_delete') {
                    return '- DELETE ' + n + ' job(s) that cannot be archived, with their files';
                }
                if (category == 'archived_files') {
                    return '- remove the result files of ' + n + ' job(s) already archived';
                }
                return '- update the phase of ' + n + ' job(s)';
            });
            if (changes.length && window.confirm('Apply these changes?\n' + changes.join('\n') + '\nAre you sure?')) {
                run_maintenance(true);
            }
        });
    });

})(jQuery);
