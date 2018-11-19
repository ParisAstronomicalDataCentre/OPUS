/*!
 * Copyright (c) 2018 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

(function($) {
    "use strict";

    var server_url;
    var client_url;
    var job_options = [];

    function get_jobnames() {
        // Get jobnames from server
        $.ajax({
            url : server_url + '/jdl',
            cache : false,
            type : 'GET',
            dataType: "json",
            success : function(json) {
                console.log(json['jobnames']);
                // Fill select
                for (var jn in json['jobnames']) {
                    job_options.push('<option value="' + json['jobnames'][jn] + '">' + json['jobnames'][jn] + '</option>')
                };
                console.log(job_options);
                get_users();
            },
            error : function(xhr, status, exception) {
                console.log(exception);
            }
        });
    }

    function get_users() {
        //var jobname = $('input[name=name]').val();
        // ajax command to get_users on UWS server
        $.ajax({
			url : server_url + '/scim/v2/Users',
			type : 'GET',
			dataType: "json",
			success : get_users_success,
			error : function(xhr, status, exception) {
				console.log(exception);
				global.showMessage('Cannot get users list from server');
				// $("#messages").append('<div class="fadeOut alert alert-' + category + ' text-center">' + msg + '</div>').delay(2000).fadeOut();
			}
		});
    }

    function get_users_success(json) {
        // Display user list with update button
        var users = json['Resources'];
        $('#server_accounts_table').empty();
        for (var u in users) {
            var user = users[u]
            var user_label = user.userName.replace('.', '_').replace('@', '_');
            //console.log(user_label);
            var row = '\
            <tr id="' + user_label + '">\
                <td class="text-center" style="vertical-align: middle;" title="Creation date: ' + user.meta.created + '">\
                    ' + user.userName + '\
                </td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="input-group">\
                        <div class="input-group-btn">\
                            <select id="roles_' + user_label + '" class="selectpicker" title="None" data_width="auto" multiple>\
                                ' + job_options.join() + '\
                            </select>\
                            <button id="button_roles_' + user_label + '" type="button" class="roles btn btn-default">\
                                <span class="glyphicon glyphicon-send"></span>\
                                <span class="hidden-xs hidden-sm hidden-md"></span>\
                            </button>\
                        </div>\
                    </div>\
                </td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="input-group">\
                        <input class="form-control" id="token_' + user_label + '" name="token_' + user_label + '" type="text" value="' + user.token + '"/>\
                        <div class="input-group-btn">\
                            <button id="button_token_' + user_label + '" type="button" class="token btn btn-default">\
                                <span class="glyphicon glyphicon-send"></span>\
                                <span class="hidden-xs hidden-sm hidden-md"></span>\
                            </button>\
                        </div>\
                    </div>\
                </td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <input id="active_' + user_label + '" name="active_' + user_label + '" type="checkbox" checked="' + user.active + '" disabled="true"/>\
                </td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="input-group-btn">\
                        <button id="button_delete_' + user_label + '" type="button" class="delete btn btn-default">\
                            <span class="glyphicon glyphicon-trash"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">Delete</span>\
                        </button>\
                        <button id="button_import_' + user_label + '" type="button" class="import btn btn-default"\
                         disabled>\
                            <span class="glyphicon glyphicon-import"></span>\
                            <span class="hidden-xs hidden-sm hidden-md">Import to client</span>\
                        </button>\
                    </div>\
                </td>\
            </tr>';
            $('#server_accounts_table').append(row);
            var roles = user.roles.split(',');
            // console.log(roles);
            $('.selectpicker').selectpicker('refresh');
            if (roles[0] == 'all') {
                $('#roles_' + user_label).selectpicker('selectAll');
            } else {
                $('#roles_' + user_label).selectpicker('val', roles);
            }
            $('#button_roles_' + user_label).click({name: user.userName, key: 'roles'}, patch_user);
            $('#button_token_' + user_label).click({name: user.userName, key: 'token'}, patch_user);
            $('#button_delete_' + user_label).click({name: user.userName}, delete_user);
        }
        // add form
        var row = '\
        <tr id="add_user">\
            <td class="text-center" style="vertical-align: middle;" width="150">\
                <input class="form-control" id="name" name="name" type="text"/>\
            </td>\
            <td class="text-center" style="vertical-align: middle;" width="300">\
                <select id="roles" class="selectpicker match-content" title="None" multiple>\
                    ' + job_options.join() + '\
                </select>\
            </td>\
            <td class="text-center" style="vertical-align: middle;">\
                <input class="form-control" id="token" name="token" type="text" placeholder="Leave empty for automatic generation"/>\
            </td>\
            <td class="text-center" style="vertical-align: middle;">\
                <input id="active" name="active" type="checkbox" checked="true" disabled="true"/>\
            </td>\
            <td class="text-center" style="vertical-align: middle;">\
                <button id="button_add_user" type="submit" class="submit btn btn-default">\
                    <span class="glyphicon glyphicon-send"></span>\
                    <span class="hidden-xs hidden-sm hidden-md">&nbsp;Submit</span>\
                </button>\
            </td>\
        </tr>';
        $('#server_accounts_table').append(row);
        $('#button_add_user').click(add_user);
        $('.selectpicker').selectpicker('refresh');
    }

    function patch_user(event) {
        var name = event.data.name;
        var key = event.data.key;
        var user_label = name.replace('.', '_').replace('@', '_');
        var value = $('#' + key + '_' + user_label).val();
        if (key == 'roles') {
            // if($('#' + key + '_' + user_label +' option:selected').length == job_options.length){
            //    console.log('all options selected');
            //     value = 'all';
            // } else {
                value = value.join(',');
            // }
        }
        console.log(name, key, value);
        $.ajax({
			url : server_url + '/scim/v2/Users/' + name,
			type : 'POST',
			data:{
                [key]: value,
            },
			dataType: "json",
			success : function(json) {
				global.showMessage('User ' + json.userName + ' patched (' + key + ')', 'info');
                get_users();
			},
            error : function(xhr, status, exception) {
				console.log(exception);
				global.showMessage('Cannot patch user', 'danger');
			}
		});
    }

    function add_user() {
        var name = $('#name').val();
        var roles = $('#roles').val();
        if (roles != null) {
            roles = roles.join(',');
        } else {
            roles = '';
        }
        var token = $('#token').val();
        $.ajax({
			url : server_url + '/scim/v2/Users/',
			type : 'POST',
			data:{
                name: name,
                roles: roles,
                token: token,
            },
			dataType: "json",
			success : function(json) {
				global.showMessage('User ' + json.userName + ' created', 'info');
                get_users();
			},
            error : function(xhr, status, exception) {
				console.log(exception);
				global.showMessage('Cannot create user', 'danger');
			}
		});
    }

    function delete_user(event) {
        var name = event.data.name;
        var isOk = window.confirm("Delete user" + name + "\nAre you sure?");
        if (isOk) {
            $.ajax({
                url : server_url + '/scim/v2/Users/' + name,
                type : 'DELETE',
                success : function() {
                    global.showMessage('User ' + name + ' deleted', 'info');
                    get_users();
                },
                error : function(xhr, status, exception) {
                    console.log(exception);
                    global.showMessage('Cannot delete user', 'danger');
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
        $('#refresh_list').click(get_users);

    });

})(jQuery);
