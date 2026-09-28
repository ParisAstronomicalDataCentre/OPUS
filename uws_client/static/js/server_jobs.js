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
                <td class="text-center" style="vertical-align: middle;">' + jdetails.contact_name + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + jdetails.type + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + jdetails.subtype + '</td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="input-group-btn">\
                        <a href="' + client_endpoint + '/job_definition/' + jobname + '" \
                        id="button_edit_' + jobname_label + '" type="button" class="btn btn-default btn-sm" \
                        title="Edit">\
                            <span class="glyphicon glyphicon-edit"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Edit</span>\
                        </a>\
                        <button id="button_history_' + jobname_label + '" type="button" class="btn btn-default btn-sm" \
                        title="History of the versions, with the differences">\
                            <span class="glyphicon glyphicon-time"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;History</span>\
                        </button>\
                        <button id="button_export_' + jobname_label + '" type="button" class="btn btn-default btn-sm" \
                        title="Export">\
                            <span class="glyphicon glyphicon-export"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Export</span>\
                        </button>\
                        <button id="button_delete_' + jobname_label + '" type="button" class="btn btn-default btn-sm" \
                        title="Delete">\
                            <span class="glyphicon glyphicon-trash"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Delete</span>\
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
            var status = (p.status == 'new') ? '<span class="label label-info">new</span>' : '<span class="label label-warning">changed</span>';
            var requested = p.validation_requested ? '<span class="glyphicon glyphicon-ok text-success"></span>' : '';
            var diff_title = (p.status == 'new') ? 'No validated version to compare with' : 'Differences with the validated version';
            tbody.append('<tr id="pending_' + i + '">'
                + '<td class="text-center"><b>' + escape_html(p.jobname) + '</b></td>'
                + '<td class="text-center">' + status + '</td>'
                + '<td class="text-center">' + escape_html(p.version) + '</td>'
                + '<td class="text-center">' + escape_html(p.submitted_by || '') + '</td>'
                + '<td class="text-center">' + escape_html(p.date) + '</td>'
                + '<td class="text-center">' + requested + '</td>'
                + '<td class="text-center"><div class="input-group-btn">'
                + '<button type="button" class="btn btn-default btn-sm pending-diff" title="' + diff_title + '"' + (p.status == 'new' ? ' disabled' : '') + '>'
                + '<span class="glyphicon glyphicon-transfer"></span><span class="hidden-xs hidden-sm hidden-md">&nbsp;Diff</span></button>'
                + '<a href="' + client_endpoint + '/job_definition/tmp/' + encodeURIComponent(p.jobname) + '" class="btn btn-default btn-sm" title="Open in the Job Definition editor">'
                + '<span class="glyphicon glyphicon-edit"></span><span class="hidden-xs hidden-sm hidden-md">&nbsp;Open</span></a>'
                + '<button type="button" class="btn btn-success btn-sm pending-validate" title="Validate: the job can then be run">'
                + '<span class="glyphicon glyphicon-ok"></span><span class="hidden-xs hidden-sm hidden-md">&nbsp;Validate</span></button>'
                + '<button type="button" class="btn btn-danger btn-sm pending-reject" title="Reject: the submitted job definition is removed">'
                + '<span class="glyphicon glyphicon-remove"></span><span class="hidden-xs hidden-sm hidden-md">&nbsp;Reject</span></button>'
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
            },
            error : ajax_error('Cannot reject the job definition ' + jobname)
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
        pending: '<span class="label label-warning">submitted</span>',
        current: '<span class="label label-success">current</span>',
        saved: '<span class="label label-default">previous</span>',
        deleted: '<span class="label label-danger">deleted</span>'
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
                        buttons += '<button type="button" class="btn btn-default btn-xs history-diff" data-from="' + previous.id + '" data-to="' + v.id
                            + '" title="Differences with the previous version (' + escape_html(previous.date) + ')">Diff with previous</button> ';
                    }
                    if (has_current && v.id != 'current' && !(previous && previous.id == 'current')) {
                        buttons += '<button type="button" class="btn btn-default btn-xs history-diff" data-from="' + v.id + '" data-to="current">Diff with current</button>';
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
                    return '<tr><td>' + escape_html(e.date) + '</td><td>' + escape_html(e.event.replace('_', ' ')) + '</td><td>'
                        + escape_html(e.user) + '</td><td>' + escape_html(details.join(', ')) + '</td></tr>';
                });
                var html = '<h5>Versions</h5><p class="text-muted small">The date of a previous version is the date of its file, '
                    + 'i.e. when it was validated.</p>'
                    + '<table class="table table-condensed table-bordered"><thead><tr><th>Date</th><th>Version</th><th>Status</th><th>Compare</th></tr></thead><tbody>'
                    + rows.join('') + '</tbody></table>'
                    + '<div id="history_diff"></div>'
                    + '<h5>Events</h5>'
                    + (events.length ? '<table class="table table-condensed table-bordered"><thead><tr><th>Date</th><th>Event</th><th>User</th><th>Details</th></tr></thead><tbody>'
                        + events.join('') + '</tbody></table>'
                        : '<p class="text-muted">No event recorded (the events are recorded since this version of OPUS).</p>');
                $('#jdl_modal_title').text('History of the job definition ' + jobname);
                $('#jdl_modal_body').html(html);
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

        // Actions
        $('#refresh_list').click(get_jobnames);
        $('#refresh_pending').click(get_pending);

    });

})(jQuery);
