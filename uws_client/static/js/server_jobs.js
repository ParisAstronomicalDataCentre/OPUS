/*!
 * Copyright (c) 2018 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var client_url;

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
                        <a href="' + client_url + '/job_definition/' + jobname + '" \
                        id="button_edit_' + jobname_label + '" type="button" class="btn btn-default btn-sm" \
                        title="Edit">\
                            <span class="glyphicon glyphicon-edit"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Edit</span>\
                        </a>\
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
            $('#button_export_' + jobname_label).click({name: jobname}, export_jdl);
            $('#button_delete_' + jobname_label).click({name: jobname}, delete_job);
        }
    }

	function edit_jdl(event) {
        var jobname = event.data.name;
        window.location = client_url + '/job_definition/' + jobname;
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

    $(document).ready( function() {
    
        // Get jobname/jobid
        server_url = $('#server_url').attr('value');
        client_url = $('#client_url').attr('value');

        // Get user list
        get_jobnames();

        // Actions
        $('#refresh_list').click(get_jobnames);

    });

})(jQuery);
