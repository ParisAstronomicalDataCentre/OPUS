/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

( function($) {
	"use strict";

    var editor;  // to use codemirror

    var type_options = {
        'param': [
            'xs:string',
            'xs:anyURI',
            'file',
            'xs:float',
            'xs:double',
            'xs:int',
            'xs:long',
            'xs:boolean',
        ],
        'result': [
            'text/plain',
            'text/xml',
            'text/x-votable+xml',
            'application/json',
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/fits',
            'video/mp4',
        ],
    };

    // ----------
    // Item list numbered

	function item_row(type, ii) {
	    switch (type) {
            // Parameters
            case 'param':
                var options = '<option>' + type_options[type].join('</option><option>') + '</option>';
                var row = '\
                    <tr id="param_' + ii + '">\
                        <td>\
                            <div class="input-group input-group-sm col-md-12">\
                                <span class="input-group-btn">\
                                    <button id="remove_param_' + ii + '" class="remove_param btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-remove" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="moveup_param_' + ii + '" class="moveup_param btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="movedown_param_' + ii + '" class="movedown_param btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                                    </button>\
                                </span>\
                                <input class="param_name form-control" style="font-weight: bold;" name="param_name_' + ii + '" type="text" placeholder="Name" />\
                                <span class="input-group-addon">=</span>\
                                <input class="param_default form-control" name="param_default_' + ii + '" type="text" placeholder="Default value" />\
                                <span class="input-group-addon">\
                                    <input class="param_required" name="param_required_' + ii + '" type="checkbox" title="Required parameter?" checked/>\
                                </span>\
                                <span class="input-group-btn">\
                                    <select class="param_type select-small selectpicker" name="param_type_' + ii + '">\
                                        ' + options + '\
                                    </select>\
                                </span>\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12">\
                                <input class="param_description form-control" name="param_description_' + ii + '" type="text" placeholder="Description" style="border-radius: 4px;" />\
                            </div>\
                            <div style="height: 8px;"></div>\
                        </td>\
                    </tr>';
                break;
            // Results
	        case 'result':
                var options = '<option>' + type_options[type].join('</option><option>') + '</option>';
                var row = '\
                    <tr id="result_' + ii + '">\
                        <td>\
                            <div class="input-group input-group-sm col-md-12">\
                                <span class="input-group-btn">\
                                    <button id="remove_result_' + ii + '" class="remove_result btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;">\
                                        <span class="glyphicon glyphicon-remove"></span>\
                                    </button>\
                                    <button id="moveup_result_' + ii + '" class="moveup_result btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="movedown_result_' + ii + '" class="movedown_result btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                                    </button>\
                                </span>\
                                <input class="result_name form-control" style="font-weight: bold;" name="result_name_' + ii + '" type="text" placeholder="Name" />\
                                <span class="input-group-addon">=</span>\
                                <input class="result_default form-control" name="result_default_' + ii + '" type="text" placeholder="Default value" />\
                                <span class="input-group-btn">\
                                    <select name="result_type_' + ii + '" class="result_type select-small selectpicker">\
                                        ' + options + '\
                                    </select>\
                                </span>\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12">\
                                <input class="result_description form-control" name="result_description_' + ii + '" type="text" placeholder="Description" style="border-radius: 4px;" />\
                            </div>\
                            <div style="height: 8px;"></div>\
                        </td>\
                    </tr>';
                break;
        }
        return row;
	}

	function add_item(type) {
	    var list_table = $('#' + type + '_list tbody');
	    var ii = list_table.children().length + 1;
        // Append row
        var row = item_row(type, ii)
        list_table.append($(row));
        // Initialize selectpicker
        $(".selectpicker").attr('data-width', '140px').selectpicker();
        // Add click events for remove/moveup/movedown
        $('#remove_' + type + '_' + ii).click( function() {
            var ids = this.id.split('_');
            var f_ii = ids.pop();
            var f_type = ids.pop();
            console.log(f_type + '_' + f_ii);
            remove_item(f_type, f_ii);
        });
        $('#moveup_' + type + '_' + ii).click( function() {
            var ids = this.id.split('_');
            var f_ii = ids.pop();
            var f_type = ids.pop();
            console.log(f_type + '_' + f_ii);
            move_item_up(f_type, f_ii);
        });
        $('#movedown_' + type + '_' + ii).click( function() {
            var ids = this.id.split('_');
            var f_ii = ids.pop();
            var f_type = ids.pop();
            console.log(f_type + '_' + f_ii);
            move_item_down(f_type, f_ii);
        });
	}

	function reset_item_numbers(type) {
	    var list_table = $('#' + type + '_list > tbody');
        list_table.children().each( function(i) {
            i++;
            if ($(this).attr('id') != type + '_' + i) {
                $(this).find('.remove_' + type).attr('id', 'remove_' + type + '_' + i);
                $(this).find('.moveup_' + type).attr('id', 'moveup_' + type + '_' + i);
                $(this).find('.movedown_' + type).attr('id', 'movedown_' + type + '_' + i);
                $(this).find('.' + type + '_name').attr('name', type + '_name_' + i);
                $(this).find('.' + type + '_default').attr('name', type + '_default_' + i);
                $(this).find('.' + type + '_required').attr('name', type + '_required_' + i);
                $(this).find('.' + type + '_type').attr('name', type + '_type_' + i);
                $(this).find('.' + type + '_description').attr('name', type + '_description_' + i);
                $(this).attr('id', type + '_' + i);
            }
        });
        $('.selectpicker').selectpicker('refresh');
	}

	function move_item_up(type, ii) {
	    var $node = $('#' + type + '_' + ii)
        $node.prev().before($node);
        reset_item_numbers(type);
	}

	function move_item_down(type, ii) {
	    var $node = $('#' + type + '_' + ii)
        $node.next().after($node);
        reset_item_numbers(type);
	}

	function remove_item(type, ii) {
        $('#' + type + '_' + ii).remove();
        reset_item_numbers(type);
    }

	function remove_last_item(type) {
	    var list_table = $('#' + type + '_list tbody');
	    list_table.children().last().remove();
    }

	function remove_all_items(type) {
	    var list_table = $('#' + type + '_list tbody');
	    list_table.children().remove();
    }

    // ----------
    // Load/Read

	function load_jdl() {
        var jobname = $('input[name=name]').val();
        // ajax command to get JDL from UWS server
        $.ajax({
			url : '/get_jdl_json/' + jobname,  //.split("/").pop(),  // to remove new/ (not needed here)
			async : true,
			type : 'GET',
			dataType: "json",
			success : function(jdl) {
				$('input[name=executionduration]').val(jdl.executionduration);
				$('input[name=quote]').val(jdl.quote);
				$('textarea[name=description]').val(jdl.description);
				// Fill param_list table
				remove_all_items('param');
				var i = 0;
				for (var param in jdl.parameters) {
				    add_item('param');
				    i++;
				    $('input[name=param_name_' + i + ']').val(param);
				    $('select[name=param_type_' + i + ']').val(jdl.parameters[param]['type']);
				    $('input[name=param_default_' + i + ']').val(jdl.parameters[param]['default']);
				    $('input[name=param_required_' + i + ']').prop("checked", jdl.parameters[param]['required'].toString().toLowerCase() == "true");
				    $('input[name=param_description_' + i + ']').val(jdl.parameters[param]['description']);
				};
				// Fill result_list table
				remove_all_items('result');
				var i = 0;
				for (var result in jdl.results) {
                    add_item('result');
				    i++;
				    $('input[name=result_name_' + i + ']').val(result);
				    $('select[name=result_type_' + i + ']').val(jdl.results[result]['content_type']);
				    $('input[name=result_default_' + i + ']').val(jdl.results[result]['default']);
				    $('input[name=result_description_' + i + ']').val(jdl.results[result]['description']);
				};
                $('.selectpicker').selectpicker('refresh');
                // ajax command to get_script from UWS server
                $.ajax({
                    url : '/get_script/' + jobname, //.split("/").pop(),
                    async : true,
                    cache : false,
                    type : 'GET',
                    dataType: "text",
                    success : function(script) {
                        // $('textarea[name=script]').val(script);
                        editor.setValue(script);
                    },
                    error : function(xhr, status, exception) {
                        console.log(exception);
                    }
                });
			},
			error : function(xhr, status, exception) {
				console.log(exception);
				$('#load_msg').text('No valid JDL found.');
				$('#load_msg').show().delay(1000).fadeOut();
			}
		});
    }

	function get_jdl() {
        var jobname = $('input[name=name]').val();
        // ajax command to get_jdl on UWS server
        $.ajax({
			url : '/get_jdl/' + jobname,  //.split("/").pop(),  // to remove new/ (not needed here)
			async : true,
			type : 'GET',
			dataType: "text",
			success : function(jdl) {
				var blob = new Blob([jdl], {type: "text/xml;charset=utf-8"});
                saveAs(blob, jobname + ".jdl");
			},
			error : function(xhr, status, exception) {
				console.log(exception);
				$('#load_msg').text('No valid JDL found.');
				$('#load_msg').show().delay(1000).fadeOut();
			}
		});
	}

    // ----------
    // ready()

	$(document).ready( function() {
	    // Script editor with CodeMirror
	    editor = CodeMirror.fromTextArea( $('textarea[name=script]')[0], {mode: "text/x-sh", lineNumbers: true } );
        $('div.CodeMirror').addClass('panel panel-default');
        // Prepare empty form
        add_item('param');
        add_item('result');
        // Get jobname from DOM (if set), and fill input form
        var jobname = $('#jobname').attr('value');
        if (jobname) {
            $('input[name=name]').val(jobname);
            load_jdl();
        };
        // Add event functions
        $('#load_jdl').click( function() {
            load_jdl();
        });
        $('#get_jdl').click( function() {
            get_jdl();
        });
        $('#validate_job').click( function() {
            jobname = $('input[name=name]').val().split("/").pop();  // remove 'new/'
            if (jobname) {
                window.location = '/client/validate_job/' + jobname;
            };
            console.log('no jobname given');
        });
        $('#cp_script').click( function() {
            jobname = $('input[name=name]').val().split("/").pop();
            if (jobname) {
                window.location = '/client/cp_script/' + jobname;  // remove 'new/'
            }
            console.log('no jobname given');
        });
        $('#add_parameter').click( function() {
            add_item('param');
        });
        $('#remove_all_parameters').click( function() {
            remove_all_items('param');
        });
        $('#add_result').click( function() {
            add_item('result');
        });
        $('#remove_all_results').click( function() {
            remove_all_items('result');
        });
        // Load JDL on return keydown for job name
        $('input[name=name]').keydown(function (event) {
            if (event.keyCode == 13) {
                event.preventDefault();
                load_jdl();
            }
        });
	}); // end ready

})(jQuery);