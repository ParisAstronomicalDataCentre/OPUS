/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

( function($) {
	"use strict";

    var editor
    var param_type_options = [
        "xs:string",
        "xs:anyURI",
        "file",
        "xs:float",
        "xs:double",
        "xs:int",
        "xs:long",
        "xs:boolean",
    ];
    var result_type_options = [
        "text/plain",
        "text/xml",
        "text/x-votable+xml",
        "application/json",
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/fits",
        "video/mp4",
    ];

    type_options = {
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
            ii = this.id.split('_').pop();
            type = this.id.split('_').pop();
            remove_item(type, ii);
        });
        $('#moveup_' + type + '_' + ii).click( function() {
            ii = this.id.split('_').pop();
            type = this.id.split('_').pop();
            move_item_up(type, ii);
        });
        $('#movedown_' + type + '_' + ii).click( function() {
            ii = this.id.split('_').pop();
            type = this.id.split('_').pop();
            move_item_down(type, ii);
        });
	}

	function reset_item_numbers(type) {
	    var list_table = $('#' + type + '_list tbody');
        list_table.each( function(i) {
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
	    var $node = $('#param_' + ii)
        $node.next().after($node);
        reset_item_numbers(type);
	}

	function remove_all_items(type) {
	    var list_table = $('#' + type + '_list tbody');
	    list_table.children().remove();
    }

	function remove_last_parameter(type) {
	    var list_table = $('#' + type + '_list tbody');
	    var ii = list_table.children().length;
	    if (ii > 0) {
    	    $('#' + type + '_' + ii).remove();
	    }
    }

	function remove_parameter(type, ii) {
        $('#' + type + '_' + ii).remove();
        reset_item_numbers(type);
    }

    // ----------
    // Parameters

	function add_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var iparam = mytable.children().length + 1;
	    var options = '<option>' + param_type_options.join('</option><option>') + '</option>';
        var row = '\
            <tr id="param_' + iparam + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_param_' + iparam + '" class="remove_param btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                <span class="glyphicon glyphicon-remove" aria-hidden="true"></span>\
                            </button>\
                            <button id="moveup_param_' + iparam + '" class="moveup_param btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                            </button>\
                            <button id="movedown_param_' + iparam + '" class="movedown_param btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                            </button>\
                        </span>\
                        <input class="param_name form-control" style="font-weight: bold;" name="param_name_' + iparam + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="param_default form-control" name="param_default_' + iparam + '" type="text" placeholder="Default value" />\
                        <span class="input-group-addon">\
                            <input class="param_required" name="param_required_' + iparam + '" type="checkbox" title="Required parameter?" checked/>\
                        </span>\
                        <span class="input-group-btn">\
                            <select class="param_type select-small selectpicker" name="param_type_' + iparam + '">\
                                ' + options + '\
                            </select>\
                        </span>\
                    </div>\
                    <div style="height: 1px;"></div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="param_description form-control" name="param_description_' + iparam + '" type="text" placeholder="Description" style="border-radius: 4px;" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        // Append row
        $('#parameter_list > tbody').append($(row));
        // Initialize selectpicker
        $(".selectpicker").attr('data-width', '140px').selectpicker();
        // Add click events for remove/moveup/movedown
        $('#remove_param_' + iparam).click( function() {
            iparam = this.id.split('_').pop();
            remove_parameter(iparam);
        });
        $('#moveup_param_' + iparam).click( function() {
            iparam = this.id.split('_').pop();
            move_parameter_up(iparam);
        });
        $('#movedown_param_' + iparam).click( function() {
            iparam = this.id.split('_').pop();
            move_parameter_down(iparam);
        });
	}

	function reset_parameter_numbers(parent) {
        parent.children().each( function(i) {
            i++;
            if ($(this).attr('id') != 'param_' + i) {
                $(this).find('.remove_param').attr('id', 'remove_param_' + i);
                $(this).find('.moveup_param').attr('id', 'moveup_param_' + i);
                $(this).find('.movedown_param').attr('id', 'movedown_param_' + i);
                $(this).find('.param_name').attr('name', 'param_name_' + i);
                $(this).find('.param_default').attr('name', 'param_default_' + i);
                $(this).find('.param_required').attr('name', 'param_required_' + i);
                $(this).find('.param_type').attr('name', 'param_type_' + i);
                $(this).find('.param_description').attr('name', 'param_description_' + i);
                $(this).attr('id', 'param_' + i);
            }
        });
        $('.selectpicker').selectpicker('refresh');
	}

	function move_parameter_up(iparam) {
	    var $node = $('#param_' + iparam)
        $node.prev().before($node);
        reset_parameter_numbers($node.parent())
	}

	function move_parameter_down(iparam) {
	    var $node = $('#param_' + iparam)
        $node.next().after($node);
        reset_parameter_numbers($node.parent())
	}

	function remove_all_parameters() {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length;
	    for (var i = nparam; i > 0; i--) {
    	    $('#param_' + i).remove();
	    }
    }

	function remove_last_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var iparam = mytable.children().length;
	    if (iparam > 0) {
    	    $('#param_' + iparam).remove();
	    }
    }

	function remove_parameter(iparam) {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length;
        $('#param_' + iparam).remove();
        reset_parameter_numbers($node.parent())
    }

    // ----------
    // Results

	function add_result() {
	    var mytable = $("#result_list tbody");
	    var iresult = mytable.children().length + 1;
	    var options = '<option>' + result_type_options.join('</option><option>') + '</option>';
        var row = '\
            <tr id="result_' + iresult + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_result_' + iresult + '" class="remove_result btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;">\
                                <span class="glyphicon glyphicon-remove"></span>\
                            </button>\
                            <button id="moveup_result_' + iresult + '" class="moveup_result btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                            </button>\
                            <button id="movedown_result_' + iresult + '" class="movedown_result btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                            </button>\
                        </span>\
                        <input class="result_name form-control" style="font-weight: bold;" name="result_name_' + iresult + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="result_default form-control" name="result_default_' + iresult + '" type="text" placeholder="Default value" />\
                        <span class="input-group-btn">\
                            <select name="result_type_' + iresult + '" class="result_type select-small selectpicker">\
                                ' + options + '\
                            </select>\
                        </span>\
                    </div>\
                    <div style="height: 1px;"></div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="result_description form-control" name="result_description_' + iresult + '" type="text" placeholder="Description" style="border-radius: 4px;" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        // Append row
        $('#result_list > tbody').append($(row));
        // Initialize selectpicker
        $(".selectpicker").attr('data-width', '140px').selectpicker();
        // Add click events for remove/moveup/movedown
        $('#remove_result_' + iresult).click( function() {
            iresult = this.id.split('_').pop();
            remove_result(iresult);
        });
        $('#moveup_result_' + iresult).click( function() {
            iresult = this.id.split('_').pop();
            move_result_up(iresult);
        });
        $('#movedown_result_' + iresult).click( function() {
            iresult = this.id.split('_').pop();
            move_result_down(iresult);
        });
	}

	function reset_result_numbers(parent) {
        parent.children().each( function(i) {
            i++;
            if ($(this).attr('id') != 'result_' + i) {
                console.log('renumber results');
                $(this).find('.remove_result').attr('id', 'remove_result_' + i);
                $(this).find('.moveup_result').attr('id', 'moveup_result_' + i);
                $(this).find('.movedown_result').attr('id', 'movedown_result_' + i);
                $(this).find('.result_name').attr('name', 'result_name_' + i);
                $(this).find('.result_default').attr('name', 'result_default_' + i);
                $(this).find('.result_type').attr('name', 'result_type_' + i);
                $(this).find('.result_description').attr('name', 'result_description_' + i);
                $(this).attr('id', 'result_' + i);
            }
        });
        $('.selectpicker').selectpicker('refresh');
	}

	function move_result_up(iresult) {
	    var $node = $('#result_' + iresult)
        $node.prev().before($node);
        reset_result_numbers($node.parent())
	}

	function move_result_down(iresult) {
	    var $node = $('#result_' + iresult)
        $node.next().after($node);
        reset_result_numbers($node.parent())
	}


	function remove_all_results() {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length;
	    for (var i = nresult; i > 0; i--) {
            $('#result_' + i).remove();
	    }
    }

	function remove_last_result() {
	    var mytable = $("#result_list tbody");
	    var iresult = mytable.children().length;
	    if (iresult > 0) {
	        $('#result_' + iresult).remove();
	    }
    }

	function remove_result(iresult) {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length;
        $('#result_' + iresult).remove();
	    for (var i = Number(iresult); i < nresult; i++) {
	        var j = i + 1;
    	    console.log(j + '->' + i);
    	    console.log($('#result_' + j).prop('id'));
    	    $('#result_' + j).prop('id', 'result_' + i);
    	    $('#remove_result_' + j).prop('id', 'remove_result_' + i);
    	    $('input[name=result_name_' + j + ']').attr('name', 'result_name_' + i);
    	    $('input[name=result_default_' + j + ']').attr('name', 'result_default_' + i);
    	    $('select[name=result_type_' + j + ']').attr('name', 'result_type_' + i);
    	    $('input[name=result_description_' + j + ']').attr('name', 'result_description_' + i);
	    }
    }

    // ----------
    // Load/Read

	function load_wadl() {
        var jobname = $('input[name=name]').val();
        // ajax command to get JDL from UWS server
        $.ajax({
			url : '/get_jdl/' + jobname, //.split("/").pop(),
			async : true,
			type : 'GET',
			dataType: "json",
			success : function(jdl) {
				$('input[name=executionduration]').val(jdl.executionduration);
				$('input[name=quote]').val(jdl.quote);
				$('textarea[name=description]').val(jdl.description);
				remove_all_parameters();
				var i = 0;
				for (var param in jdl.parameters) {
				    //add_parameter();
				    add_item('param');
				    i++;
				    $('input[name=param_name_' + i + ']').val(param);
				    $('select[name=param_type_' + i + ']').val(jdl.parameters[param]['type']);
				    $('input[name=param_default_' + i + ']').val(jdl.parameters[param]['default']);
				    $('input[name=param_required_' + i + ']').prop("checked", jdl.parameters[param]['required'].toLowerCase() == "true");
				    $('input[name=param_description_' + i + ']').val(jdl.parameters[param]['description']);
				};
				remove_all_results();
				var i = 0;
				for (var result in jdl.results) {
				    //add_result();
                    add_item('result');
				    i++;
				    $('input[name=result_name_' + i + ']').val(result);
				    $('select[name=result_type_' + i + ']').val(jdl.results[result]['mediaType']);
				    $('input[name=result_default_' + i + ']').val(jdl.results[result]['default']);
				    $('input[name=result_description_' + i + ']').val(jdl.results[result]['description']);
				};
                $('.selectpicker').selectpicker('refresh');
                // ajax command to get_script on UWS server
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
				$('#load_msg').text('No valid WADL found.');
				$('#load_msg').show().delay(1000).fadeOut();
			}
		});
    }

	function get_wadl() {
        var jobname = $('input[name=name]').val();
        // ajax command to get_wadl on UWS server
        $.ajax({
			url : '/get_wadl/' + jobname, //.split("/").pop(),
			async : true,
			type : 'GET',
			dataType: "text",
			success : function(wadl) {
				var blob = new Blob([wadl], {type: "text/xml;charset=utf-8"});
                saveAs(blob, jobname + ".wadl");
			},
			error : function(xhr, status, exception) {
				console.log(exception);
				$('#load_msg').text('No valid WADL found.');
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
        //add_parameter();
        //add_result();
        add_item('param');
        add_item('result');
        // Get jobname from DOM (if set), and fill input form
        var jobname = $('#jobname').attr('value');
        if (jobname) {
            $('input[name=name]').val(jobname);
            load_wadl();
        };
        // Add event functions
        $('#load_wadl').click( function() { load_wadl(); });
        $('#get_wadl').click( function() { get_wadl(); });
        $('#validate_job').click( function() {
            jobname = $('input[name=name]').val().split("/").pop();
            if (jobname) {
                window.location = '/config/validate_job/' + jobname;
            };
            console.log('no jobname given');
        });
        $('#cp_script').click( function() {
            jobname = $('input[name=name]').val().split("/").pop();
            if (jobname) {
                window.location = '/config/cp_script/' + jobname;
            }
            console.log('no jobname given');
        });
        $('#add_parameter').click( function() { add_item('param'); });
        $('#remove_last_parameter').click( function() { remove_last_item('param'); });
        $('#remove_all_parameters').click( function() { remove_all_items('param'); });
        $('#add_result').click( function() { add_item('result'); });
        $('#remove_last_result').click( function() { remove_last_item('result'); });
        $('#remove_all_results').click( function() { remove_all_items('result'); });
        $('input[name=name]').keydown(function (event) {
            if (event.keyCode == 13) {
                event.preventDefault();
                load_wadl();
            }
        });
	}); // end ready

})(jQuery);