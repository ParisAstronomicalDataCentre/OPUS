/*!
 * Copyright (c) 2018 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var server_endpoint;
    var client_endpoint;

    function get_jobnames() {
        // Get jobnames from server
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl',
            cache : false,
            type : 'GET',
            dataType: "json",
            success : function(json) {
                $('#loading').hide();
                console.log(json);
                // Fill table
                get_jobnames_success(json)
            },
            error : function(xhr, status, exception) {
                $('#loading').hide();
                console.log(exception);
            }
        });
    }

    function get_jobnames_success(json) {
        // Display user list with update button
        var jobnames = json['jobnames']
        var details = json['details']
        $('#server_jobs_thead').empty();
        $('#server_jobs_tbody').empty();
        var row = '\
            <tr>\
                <th class="text-center">Job name</th>\
                <th class="text-center">Version</th>\
                <th class="text-center">Contact</th>\
                <th class="text-center">Type</th>\
                <th class="text-center">Subtype</th>\
                <th class="text-center">Actions</th>\
            </tr>';
        $('#server_jobs_thead').append(row);
        for (var j in jobnames) {
            var jobname = jobnames[j]
            var jobname_label = jobname.replace(/\./g, "_").replace(/@/g, "_");
            var jdetails = details[jobname]
            //console.log(user.userName);
            var row = '\
            <tr id="' + jobname_label + '">\
                <td class="text-center" style="vertical-align: middle;"><b>' + jobname + '</b></td>\
                <td class="text-center" style="vertical-align: middle;">' + jdetails.version + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + (dates[jobname] || '').replace('T'') + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + jdetails.contact_name + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + jdetails.type + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + jdetails.subtype + '</td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="input-group-btn">\
                        <a href="' + client_endpoint + '/job_definition/' + jobname + '" \
                        id="button_edit_' + jobname_label + '" type="button" class="btn btn-outline-secondary btn-sm" \
                        title="Edit">\
                            <span class="bi bi-pencil-square"></span>\
                            <span class="d-none d-lg-inline">&nbsp;Edit</span>\
                        </a>\
                        <button id="button_history_' + jobname_label + '" type="button" class="btn btn-outline-secondary btn-sm" \
                        title="History of the versions, with the differences">\
                            <span class="bi bi-clock"></span>\
                            <span class="d-none d-lg-inline">&nbsp;History</span>\
                        </button>\
                        <button id="button_export_' + jobname_label + '" type="button" class="btn btn-outline-secondary btn-sm" \
                        title="Export">\
                            <span class="bi bi-box-arrow-up"></span>\
                            <span class="d-none d-lg-inline">&nbsp;Export</span>\
                        </button>\
                        <button id="button_delete_' + jobname_label + '" type="button" class="btn btn-outline-secondary btn-sm" \
                        title="Delete">\
                            <span class="bi bi-trash"></span>\
                            <span class="d-none d-lg-inline">&nbsp;Delete</span>\
                        </button>\
                    </div>\
                </td>\
            </tr>';
            $('#server_jobs_tbody').append(row);
            //$('#button_edit_' + jobname_label).click({name: jobname}, edit_jdl);
            $('#button_history_' + jobname_label).click({name: jobname}, show_history);
            $('#button_export_' + jobname_label).click({name: jobname}, export_jdl);
            $('#button_delete_' + jobname_label).click({name: jobname}, delete_job);
        }
    }

	function edit_jdl(event) {
        var jobname = event.data.name;
        window.location = client_endpoint + '/job_definition/' + jobname;
    }

	function export_jdl(event) {
        var jobname = event.data.name;
        if (jobname.length > 0) {
            if (jobname.search("new/") == -1) {
                $('#loading').show();
                // ajax command to get JDL file from UWS server
                $.ajax({
                    url : server_url + '/jdl/' + jobname,  //.split("/").pop(),  // to remove new/ (not needed here)
                    type : 'GET',
                    dataType: "text",
                    success : function(response, status, xhr) {
                        // check for a filename
                        var filename = "";
                        var disposition = xhr.getResponseHeader('Content-Disposition');
                        if (disposition && disposition.indexOf('attachment') !== -1) {
                            var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                            var matches = filenameRegex.exec(disposition);
                            if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
                        };
                        var type = xhr.getResponseHeader('Content-Type');
                        var blob = new Blob([response], { type: type });
                        $('#loading').hide();
                        //var blob = new Blob([jdl], {type: "text/xml;charset=utf-8"});
                        //var filename = jobname + ".xml";
                        //saveAs(blob, jobname + ".jdl");
                        var link = document.createElement('a');
                        link.href = window.URL.createObjectURL(blob);
                        link.download = filename;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    },
                    error : function(xhr, status, exception) {
                        $('#loading').hide();
                        console.log(exception);
                        global.showMessage(exception, 'danger');
                        //$('#load_msg').text(exception);
                        //$('#load_msg').show().delay(2000).fadeOut();
                    }
                });
            } else {
                global.showMessage('Cannot export non-validated job', 'warning');
            };
        } else {
            global.showMessage('No job name given', 'warning');
        };
	};

    function delete_job(event) {
        $('#loading').show();
        var name = event.data.name;
        var isOk = window.confirm("Delete job" + name + "\nAre you sure?");
        if (isOk) {
            $.ajax({
                url : server_url + '/jdl/' + name,
                type : 'DELETE',
                success : function() {
                    $('#loading').hide();
                    global.showMessage('Job definition "' + name + '" has been archived and deleted', 'success');
                    get_jobnames();
                    get_inactive();
                },
                error : function(xhr, status, exception) {
                    $('#loading').hide();
                    console.log(exception);
                    global.showMessage('Cannot delete job definition', 'danger');
                }
            });
        };
    }

    // ----------
    // Job definitions to validate, history and diff of the versions

    function escape_html(text) {
        return $('<div/>').text(text == null ? '' : text).html();
    }

    function ajax_error(msg) {
        return function (xhr, status, exception) {
            $('#loading').hide();
            global.showMessage(msg + ' (' + xhr.status + ': ' + (exception || status) + ')', 'danger');
        };
    }

    function get_pending() {
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl_admin/pending',
            cache : false,
            type : 'GET',
            dataType : 'json',
            success : function (json) {
                $('#loading').hide();
                show_pending(json.pending);
            },
            error : ajax_error('Cannot get the job definitions to validate')
        });
    }

    function show_pending(pending) {
        var tbody = $('#pending_tbody');
        tbody.empty();
        $('#pending_table').toggle(pending.length > 0);
        $('#pending_empty').toggle(pending.length == 0);
        $.each(pending, function (i, p) {
            var status = (p.status == 'new') ? '<span class="badge text-bg-info">new</span>' : '<span class="badge text-bg-warning">changed</span>';
            var requested = p.validation_requested ? '<span class="bi bi-check-lg text-success"></span>' : '';
            var diff_title = (p.status == 'new') ? 'No validated version to compare with' : 'Differences with the validated version';
            tbody.append('<tr id="pending_' + i + '">'
                + '<td class="text-center"><b>' + escape_html(p.jobname) + '</b></td>'
                + '<td class="text-center">' + status + '</td>'
                + '<td class="text-center">' + escape_html(p.version) + '</td>'
                + '<td class="text-center">' + escape_html(p.submitted_by || '') + '</td>'
                + '<td class="text-center">' + escape_html(p.date) + '</td>'
                + '<td class="text-center">' + requested + '</td>'
                + '<td class="text-center"><div class="input-group-btn">'
                + '<button type="button" class="btn btn-outline-secondary btn-sm pending-diff" title="' + diff_title + '"' + (p.status == 'new' ? ' disabled' : '') + '>'
                + '<span class="bi bi-arrow-left-right"></span><span class="d-none d-lg-inline">&nbsp;Diff</span></button>'
                + '<a href="' + client_endpoint + '/job_definition/tmp/' + encodeURIComponent(p.jobname) + '" class="btn btn-outline-secondary btn-sm" title="Open in the Job Definition editor">'
                + '<span class="bi bi-pencil-square"></span><span class="d-none d-lg-inline">&nbsp;Open</span></a>'
                + '<button type="button" class="btn btn-success btn-sm pending-validate" title="Validate: the job can then be run">'
                + '<span class="bi bi-check-lg"></span><span class="d-none d-lg-inline">&nbsp;Validate</span></button>'
                + '<button type="button" class="btn btn-danger btn-sm pending-reject" title="Reject: the submitted job definition is removed">'
                + '<span class="bi bi-x-lg"></span><span class="d-none d-lg-inline">&nbsp;Reject</span></button>'
                + '</div></td></tr>');
            var row = $('#pending_' + i);
            row.find('.pending-diff').click(function () {
                show_diff(p.jobname, 'current', 'pending', 'Job definition ' + p.jobname + ': validated version → submitted version');
            });
            row.find('.pending-validate').click(function () { validate_pending(p.jobname); });
            row.find('.pending-reject').click(function () { reject_pending(p.jobname); });
        });
    }

    function validate_pending(jobname) {
        if (!window.confirm('Validate the job definition ' + jobname + '?\nThe job can then be run (by the users with this role).')) { return; }
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl/tmp/' + encodeURIComponent(jobname) + '/validate',
            type : 'POST',
            dataType : 'json',
            success : function () {
                $('#loading').hide();
                global.showMessage('Job definition ' + jobname + ' validated', 'success');
                get_pending();
                get_jobnames();
                get_inactive();
            },
            error : ajax_error('Cannot validate the job definition ' + jobname)
        });
    }

    function reject_pending(jobname) {
        var message = window.prompt('Reject the job definition ' + jobname + ' (the submitted version is removed).\nMessage for the history (optional):', '');
        if (message === null) { return; }
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl/tmp/' + encodeURIComponent(jobname) + '?MESSAGE=' + encodeURIComponent(message),
            type : 'DELETE',
            success : function () {
                $('#loading').hide();
                global.showMessage('Job definition ' + jobname + ' rejected', 'success');
                get_pending();
                get_inactive();
            },
            error : ajax_error('Cannot reject the job definition ' + jobname)
        });
    }

    function get_inactive() {
        $.ajax({
            url : server_url + '/jdl_admin/inactive',
            cache : false,
            type : 'GET',
            dataType : 'json',
            success : function (json) { show_inactive(json.inactive); },
            error : ajax_error('Cannot get the deleted job definitions')
        });
    }

    function show_inactive(inactive) {
        var tbody = $('#inactive_tbody');
        tbody.empty();
        $('#inactive_table').toggle(inactive.length > 0);
        $('#inactive_empty').toggle(inactive.length == 0);
        $.each(inactive, function (i, j) {
            var status = (j.status == 'deleted') ? '<span class="badge text-bg-danger">deleted</span>'
                : '<span class="badge text-bg-secondary">never validated</span>';
            var last = j.last_version ? escape_html(j.last_version.version) : '';
            var restore_title = j.last_version ? 'Validate again the last version (' + escape_html(j.last_version.date) + ')' : 'No version to restore';
            tbody.append('<tr id="inactive_' + i + '">'
                + '<td class="text-center"><b>' + escape_html(j.jobname) + '</b></td>'
                + '<td class="text-center">' + status + '</td>'
                + '<td class="text-center">' + last + '</td>'
                + '<td class="text-center">' + escape_html(j.date || '') + '</td>'
                + '<td class="text-center">' + escape_html(j.user || '') + '</td>'
                + '<td class="text-center"><div class="input-group-btn">'
                + '<button type="button" class="btn btn-outline-secondary btn-sm inactive-history" title="History of the versions, with the differences">'
                + '<span class="bi bi-clock"></span><span class="d-none d-lg-inline">&nbsp;History</span></button>'
                + '<button type="button" class="btn btn-outline-secondary btn-sm inactive-restore" title="' + restore_title + '"' + (j.last_version ? '' : ' disabled') + '>'
                + '<span class="bi bi-arrow-repeat"></span><span class="d-none d-lg-inline">&nbsp;Restore</span></button>'
                + '</div></td></tr>');
            var row = $('#inactive_' + i);
            row.find('.inactive-history').click({name: j.jobname}, show_history);
            if (j.last_version) {
                row.find('.inactive-restore').click(function () { restore_version(j.jobname, j.last_version); });
            }
        });
    }

    function restore_version(jobname, version) {
        var msg = 'Validate again the version ' + version.version + ' of ' + jobname + ' (' + version.date + ')?\n'
            + 'The job can then be run again. The current version, if any, is kept in the history.';
        if (!window.confirm(msg)) { return; }
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl_admin/' + encodeURIComponent(jobname) + '/restore',
            type : 'POST',
            data : {VERSION: version.id},
            dataType : 'json',
            success : function () {
                $('#loading').hide();
                $('#jdl_modal').modal('hide');
                global.showMessage('Version ' + version.version + ' of ' + jobname + ' restored', 'success');
                get_jobnames();
                get_inactive();
            },
            error : ajax_error('Cannot restore the job definition ' + jobname)
        });
    }

    function diff_html(text) {
        // Unified diff, lines colored
        if (!text) { return '<span class="text-muted">No difference</span>'; }
        return text.split('\n').map(function (line) {
            var cls = '';
            if (line.indexOf('+++') == 0 || line.indexOf('---') == 0) { cls = 'diff-file'; }
            else if (line.indexOf('@@') == 0) { cls = 'diff-hunk'; }
            else if (line.indexOf('+') == 0) { cls = 'diff-add'; }
            else if (line.indexOf('-') == 0) { cls = 'diff-del'; }
            return cls ? '<span class="' + cls + '">' + escape_html(line) + '</span>' : escape_html(line);
        }).join('\n');
    }

    function load_diff(jobname, from, to, target) {
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl_admin/' + encodeURIComponent(jobname) + '/diff',
            data : {FROM: from, TO: to},
            cache : false,
            type : 'GET',
            dataType : 'json',
            success : function (json) {
                $('#loading').hide();
                target.html('<h5>Job definition</h5><pre class="jdl-diff">' + diff_html(json.definition) + '</pre>'
                    + '<h5>Script</h5><pre class="jdl-diff">' + diff_html(json.script) + '</pre>');
            },
            error : ajax_error('Cannot compare the versions')
        });
    }

    function show_diff(jobname, from, to, title) {
        $('#jdl_modal_title').text(title);
        $('#jdl_modal_body').html('<div id="modal_diff"></div>');
        $('#jdl_modal').modal('show');
        load_diff(jobname, from, to, $('#modal_diff'));
    }

    var KINDS = {
        pending: '<span class="badge text-bg-warning">submitted</span>',
        current: '<span class="badge text-bg-success">current</span>',
        saved: '<span class="badge text-bg-secondary">previous</span>',
        deleted: '<span class="badge text-bg-danger">deleted</span>'
    };

    function show_history(event) {
        var jobname = event.data.name;
        $('#loading').show();
        $.ajax({
            url : server_url + '/jdl_admin/' + encodeURIComponent(jobname) + '/history',
            cache : false,
            type : 'GET',
            dataType : 'json',
            success : function (json) {
                $('#loading').hide();
                var versions = json.versions;
                var has_current = versions.some(function (v) { return v.id == 'current'; });
                var rows = versions.map(function (v, i) {
                    // previous version: the next one in the list (most recent first), the pending version is compared with the current one
                    var previous = (i + 1 < versions.length) ? versions[i + 1] : null;
                    var buttons = '';
                    if (previous) {
                        buttons += '<button type="button" class="btn btn-outline-secondary btn-sm history-diff" data-from="' + previous.id + '" data-to="' + v.id
                            + '" title="Differences with the previous version (' + escape_html(previous.date) + ')">Diff with previous</button> ';
                    }
                    if (has_current && v.id != 'current' && !(previous && previous.id == 'current')) {
                        buttons += '<button type="button" class="btn btn-outline-secondary btn-sm history-diff" data-from="' + v.id + '" data-to="current">Diff with current</button> ';
                    }
                    if (v.kind == 'saved' || v.kind == 'deleted') {
                        buttons += '<button type="button" class="btn btn-warning btn-sm history-restore" data-index="' + i
                            + '" title="Validate again this version (the current version, if any, is kept)">Restore</button>';
                    }
                    return '<tr><td>' + escape_html(v.date) + '</td><td>' + escape_html(v.version) + '</td><td>'
                        + (KINDS[v.kind] || escape_html(v.kind)) + '</td><td>' + buttons + '</td></tr>';
                });
                var events = json.events.slice().reverse().map(function (e) {
                    var details = [];
                    if (e.version) { details.push('version ' + e.version); }
                    if (e.via) { details.push('via ' + e.via); }
                    if (e.message) { details.push('"' + e.message + '"'); }
                    if (e.email == 'failed') { details.push('email not sent'); }
                    if (e.restored) { details.push('from ' + e.restored); }
                    return '<tr><td>' + escape_html(e.date) + '</td><td>' + escape_html(e.event.replace('_', ' ')) + '</td><td>'
                        + escape_html(e.user) + '</td><td>' + escape_html(details.join(', ')) + '</td></tr>';
                });
                var html = '<h5>Versions</h5><p class="text-muted small">The date of a previous version is the date of its file, '
                    + 'i.e. when it was validated.</p>'
                    + '<table class="table table-sm table-bordered"><thead><tr><th>Date</th><th>Version</th><th>Status</th><th>Actions</th></tr></thead><tbody>'
                    + rows.join('') + '</tbody></table>'
                    + '<div id="history_diff"></div>'
                    + '<h5>Events</h5>'
                    + (events.length ? '<table class="table table-sm table-bordered"><thead><tr><th>Date</th><th>Event</th><th>User</th><th>Details</th></tr></thead><tbody>'
                        + events.join('') + '</tbody></table>'
                        : '<p class="text-muted">No event recorded (the events are recorded since this version of OPUS).</p>');
                $('#jdl_modal_title').text('History of the job definition ' + jobname);
                $('#jdl_modal_body').html(html);
                $('#jdl_modal_body .history-restore').click(function () {
                    restore_version(jobname, versions[$(this).data('index')]);
                });
                $('#jdl_modal_body .history-diff').click(function () {
                    var from = $(this).data('from'), to = $(this).data('to');
                    $('#history_diff').html('<p><b>' + escape_html(from) + ' → ' + escape_html(to) + '</b></p><div id="history_diff_content"></div>');
                    load_diff(jobname, from, to, $('#history_diff_content'));
                });
                $('#jdl_modal').modal('show');
            },
            error : ajax_error('Cannot get the history of ' + jobname)
        });
    }

    $(document).ready( function() {
    
        // Get jobname/jobid
        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');

        // Job definitions to validate, and validated job definitions
        get_pending();
        get_jobnames();
        get_inactive();

        // Actions
        $('#refresh_list').click(get_jobnames);
        $('#refresh_pending').click(get_pending);
        $('#refresh_inactive').click(get_inactive);

    });

})(jQuery);
