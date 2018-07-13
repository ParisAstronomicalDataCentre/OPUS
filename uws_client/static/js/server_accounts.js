/*!
 * Copyright (c) 2018 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var endpoint;

    function get_users() {
        //var jobname = $('input[name=name]').val();
        // ajax command to get_users on UWS server
        $.ajax({
			url : server_url + '/scim/v2/Users',
			type : 'GET',
			dataType: "json",
			success : function(json) {
                // Display user list with update button
                var users = json['Resources'];
                for (var u in users) {
                    var user = users[u]
                    console.log(user.userName);
                    var row = '\
            <div id="' + user.userName + '" class="row form-group">\
                <label class="col-md-2 control-label">' + user.userName + '</label>\
                <div class="col-md-4 controls ">\
                    <div class="input-group">\
                        <input class="form-control" id="roles_' + user.userName + '" name="roles_' + user.userName + '" type="text" value="' + user.roles + '"/>\
                        <div class="input-group-btn">\
                            <button type="button" class="start btn btn-default">\
                                <span class="glyphicon glyphicon-send"></span>\
                                <span class="hidden-xs hidden-sm hidden-md"></span>\
                            </button>\
                        </div>\
                    </div>\
                </div>\
                <div class="col-md-4 controls">\
                    <div class="input-group">\
                        <input class="form-control" id="token_' + user.userName + '" name="token_' + user.userName + '" type="text" value="' + user.token + '"/>\
                        <div class="input-group-btn">\
                            <button type="button" class="start btn btn-default">\
                                <span class="glyphicon glyphicon-send"></span>\
                                <span class="hidden-xs hidden-sm hidden-md"></span>\
                            </button>\
                        </div>\
                    </div>\
                </div>\
                <div class="col-md-2">\
                    <button type="button" class="delete btn btn-default">\
                        <span class="glyphicon glyphicon-trash"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">Delete</span>\
                    </button>\
                </div>\
            </div>';
                    $('#server_accounts_patch').append(row)
                }
			},
			error : function(xhr, status, exception) {
				console.log(exception);
				global.showMessage('Cannot get users list from server');
				// $("#messages").append('<div class="fadeOut alert alert-' + category + ' text-center">' + msg + '</div>').delay(2000).fadeOut();
			}
		});
    }


    function patch_user(name, key, value) {

    }


    $(document).ready( function() {
    
        // Get jobname/jobid
        server_url = $('#server_url').attr('value');
        endpoint = $('#endpoint').attr('value');

        // Get user list
        get_users();

        // Display user list with update button


        // catch the form's submit event to validate form
        $('#server_accounts_patch').submit(function(event) {
            event.preventDefault();
            var formData = new FormData($('#job_params')[0]);
//            $('input[type=file]').each( function() {
//                console.log('Adding: ' + $(this).attr('name'));
//                console.log($(this)[0].files[0]);
//                formData.append($(this).attr('name'), $(this)[0].files[0]);
//            });
            uws_client.createJob(jobname, formData);
        });

    });

})(jQuery);
