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
                console.log(json['jobnames']);
                // Fill table
                get_jobnames_success(json['jobnames'])
            },
            error : function(xhr, status, exception) {
                $('#loading').hide();
                console.log(exception);
            }
        });
    }

    function get_jobnames_success(jobnames) {
        // Display user list with update button
        $('#server_jobs_table').empty();
        for (var j in jobnames) {
            var job = jobnames[j]
            //console.log(user.userName);
            var row = '\
            <tr id="' + job + '">\
                <td class="text-left" style="vertical-align: middle;">\
                    ' + job + '\
                </td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="input-group-btn">\
                        <button id="button_edit_' + job + '" type="button" class="btn btn-default btn-sm">\
                            <span class="glyphicon glyphicon-edit"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">Edit</span>\
                        </button>\
                        <button id="button_download_' + job + '" type="button" class="btn btn-default btn-sm">\
                            <span class="glyphicon glyphicon-download"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">Download</span>\
                        </button>\
                        <button id="button_delete_' + job + '" type="button" class="btn btn-default btn-sm">\
                            <span class="glyphicon glyphicon-trash"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">Delete</span>\
                        </button>\
                    </div>\
                </td>\
            </tr>';
            $('#server_jobs_table').append(row);
            $('#button_edit_' + job).click({name: job}, edit_jdl);
            $('#button_download_' + job).click({name: job}, save_jdl);
            $('#button_delete_' + job).click({name: job}, delete_job);
        }
    }

	function edit_jdl(event) {
        var jobname = event.data.name;
        window.location = client_url + '/job_definition/' + jobname;
    }

	function save_jdl(event) {
        $('#loading').show();
        var jobname = event.data.name;
        // ajax command to save_jdl from UWS server
        $.ajax({
			url : server_url + '/jdl/' + jobname,  //.split("/").pop(),  // to remove new/ (not needed here)
			type : 'GET',
			dataType: "text",
			success : function(jdl) {
                $('#loading').hide();
				var blob = new Blob([jdl], {type: "text/xml;charset=utf-8"});
				var filename = jobname + ".xml";
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
                global.showMessage('Cannot download job', 'danger');
			}
		});
	}

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
                    global.showMessage('Job ' + name + ' deleted', 'info');
                    get_jobnames();
                },
                error : function(xhr, status, exception) {
                    $('#loading').hide();
                    console.log(exception);
                    global.showMessage('Cannot delete job', 'danger');
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
        $('#new_job_definition').click(function(){
            window.location = client_url + '/job_definition/';
        });

    });

})(jQuery);
