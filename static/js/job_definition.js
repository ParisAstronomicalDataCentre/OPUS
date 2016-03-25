( function($) {
	"use strict";

    var editor
    var param_type_options = [
        "xs:string</option>",
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
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/fits",
        "video/mp4",
    ];

	function add_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var iparam = mytable.children().length;
	    var options = '<option>' + param_type_options.join('</option><option>') + '</option>';
        var row = '\
            <tr id="param_' + iparam + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_param_' + iparam + '" class="btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;" >\
                                <span class="glyphicon glyphicon-remove"></span>\
                            </button>\
                        </span>\
                        <input class="form-control" style="font-weight: bold;" name="param_name_' + iparam + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="form-control" name="param_default_' + iparam + '" type="text" placeholder="Default value" />\
                        <span class="input-group-addon">\
                            <input title="Required parameter?" name="param_required_' + iparam + '" type="checkbox" checked/>\
                        </span>\
                        <span class="input-group-btn">\
                            <select name="param_type_' + iparam + '" class="select-small selectpicker">\
                                ' + options + '\
                            </select>\
                        </span>\
                    </div>\
                    <div style="height: 1px;"></div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="form-control" name="param_description_' + iparam + '" type="text" placeholder="Description" style="border-radius: 4px;" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        $(row).insertBefore('#parameter_list > tbody > tr:last');
        $(".selectpicker").attr('data-width', '140px').selectpicker();
        $('#remove_param_' + iparam).click( function() {
            iparam = this.id.split('_').pop();
            remove_parameter(iparam);
        });
//        $('#moveup_param_' + iparam).click( function() {
//            iparam = this.id.split('_').pop();
//            move_parameter_up(iparam);
//        });
//        $('#movedw_param_' + iparam).click( function() {
//            iparam = this.id.split('_').pop();
//            move_parameter_down(iparam);
//        });
	}

	function remove_all_parameters() {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length - 1;
	    for (var i = nparam; i > 0; i--) {
    	    $('#param_' + i).remove();
	    }
    }

	function remove_last_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var iparam = mytable.children().length - 1;
	    if (iparam > 0) {
    	    $('#param_' + iparam).remove();
	    }
    }

	function remove_parameter(iparam) {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length - 1;
        $('#param_' + iparam).remove();
	    for (var i = Number(iparam); i < nparam; i++) {
	        var j = i + 1;
    	    console.log(j + '->' + i);
    	    console.log($('#param_' + j).prop('id'));
    	    $('#param_' + j).prop('id', 'param_' + i);
    	    $('#remove_param_' + j).prop('id', 'remove_param_' + i);
    	    $('input[name=param_name_' + j + ']').attr('name', 'param_name_' + i);
    	    $('input[name=param_default_' + j + ']').attr('name', 'param_default_' + i);
    	    $('input[name=param_required_' + j + ']').attr('name', 'param_required_' + i);
    	    $('select[name=param_type_' + j + ']').attr('name', 'param_type_' + i);
    	    $('input[name=param_description_' + j + ']').attr('name', 'param_description_' + i);
	    }
    }

	function add_result() {
	    var mytable = $("#result_list tbody");
	    var iresult = mytable.children().length;
	    var options = '<option>' + result_type_options.join('</option><option>') + '</option>';
        var row = '\
            <tr id="result_' + iresult + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_result_' + iresult + '" class="btn btn-default" type="button" style="border-bottom-left-radius: 4px; border-top-left-radius: 4px;">\
                                <span class="glyphicon glyphicon-remove"></span>\
                            </button>\
                        </span>\
                        <input class="form-control" style="font-weight: bold;" name="result_name_' + iresult + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="form-control" name="result_default_' + iresult + '" type="text" placeholder="Default value" />\
                        <span class="input-group-btn">\
                            <select name="result_type_' + iresult + '" class="select-small selectpicker">\
                                ' + options + '\
                            </select>\
                        </span>\
                    </div>\
                    <div style="height: 1px;"></div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="form-control" name="result_description_' + iresult + '" type="text" placeholder="Description" style="border-radius: 4px;" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        $(row).insertBefore('#result_list > tbody > tr:last');
        $(".selectpicker").attr('data-width', '140px').selectpicker();
        $('#remove_result_' + iresult).click( function() {
            iresult = this.id.split('_').pop();
            remove_result(iresult);
        });
	}

	function remove_all_results() {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length - 1;
	    for (var i = nresult; i > 0; i--) {
            $('#result_' + i).remove();
	    }
    }

	function remove_last_result() {
	    var mytable = $("#result_list tbody");
	    var iresult = mytable.children().length - 1;
	    if (iresult > 0) {
	        $('#result_' + iresult).remove();
	    }
    }

	function remove_result(iresult) {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length - 1;
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

	function load_wadl() {
        var jobname = $('input[name=name]').val();
        // ajax command to get_wadl on UWS server
        $.ajax({
			url : '/get_wadl_json/' + jobname, //.split("/").pop(),
			async : true,
			type : 'GET',
			dataType: "json",
			success : function(wadl) {
				$('input[name=executionduration]').val(wadl.executionduration);
				$('input[name=quote]').val(wadl.quote);
				$('textarea[name=description]').val(wadl.description);
				remove_all_parameters();
				var i = 0;
				for (var param in wadl.parameters) {
				    add_parameter();
				    i++;
				    $('input[name=param_name_' + i + ']').val(param);
				    $('select[name=param_type_' + i + ']').val(wadl.parameters[param]['type']);
				    $('input[name=param_default_' + i + ']').val(wadl.parameters[param]['default']);
				    $('input[name=param_required_' + i + ']').prop("checked", wadl.parameters[param]['required'].toLowerCase() == "true");
				    $('input[name=param_description_' + i + ']').val(wadl.parameters[param]['description']);
				};
				remove_all_results();
				var i = 0;
				for (var result in wadl.results) {
				    add_result();
				    i++;
				    $('input[name=result_name_' + i + ']').val(result);
				    $('select[name=result_type_' + i + ']').val(wadl.results[result]['mediaType']);
				    $('input[name=result_default_' + i + ']').val(wadl.results[result]['default']);
				    $('input[name=result_description_' + i + ']').val(wadl.results[result]['description']);
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

	$(document).ready( function() {
	    // Script editor with CodeMirror
	    editor = CodeMirror.fromTextArea( $('textarea[name=script]')[0], {mode: "text/x-sh", lineNumbers: true } );
        $('div.CodeMirror').addClass('panel panel-default');
        // Prepare empty form
        add_parameter();
        add_result();
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
            jobname = $('input[name=name]').split("/").pop();
            location.href = '/config/validate_job/' + jobname;
        });
        $('#cp_script').click( function() {
            jobname = $('input[name=name]').split("/").pop();
            location.href = '/config/cp_script/' + jobname;
        });
        $('#add_parameter').click( function() { add_parameter(); });
        $('#remove_last_parameter').click( function() { remove_last_parameter(); });
        $('#remove_all_parameters').click( function() { remove_all_parameters(); });
        $('#add_result').click( function() { add_result(); });
        $('#remove_last_result').click( function() { remove_last_result(); });
        $('#remove_all_results').click( function() { remove_all_results(); });
        $('input[name=name]').keydown(function (event) {
            if (event.keyCode == 13) {
                event.preventDefault();
                load_wadl();
            }
        });
	}); // end ready

})(jQuery);