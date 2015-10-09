( function($) {
	"use strict";

	function add_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length;
        var row = '\
            <tr id="param_' + nparam + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_param_' + nparam + '" class="btn btn-default" type="button">\
                                <span class="glyphicon glyphicon-remove"></span>\
                            </button>\
                        </span>\
                        <input class="form-control" style="font-weight: bold;" name="param_name_' + nparam + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="form-control" name="param_default_' + nparam + '" type="text" placeholder="Default value" />\
                        <span class="input-group-addon">\
                            <input title="Required parameter?" name="param_required_' + nparam + '" type="checkbox" checked/>\
                        </span>\
                        <span class="input-group-btn">\
                            <select name="param_type_' + nparam + '" class="btn btn-default">\
                                <option>xs:string</option>\
                                <option>xs:anyURI</option>\
                                <option>file</option>\
                                <option>xs:float</option>\
                                <option>xs:double</option>\
                                <option>xs:int</option>\
                                <option>xs:long</option>\
                                <option>xs:boolean</option>\
                            </select>\
                        </span>\
                    </div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="form-control" name="param_description_' + nparam + '" type="text" placeholder="Description" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        $(row).insertBefore('#parameter_list > tbody > tr:last');
        //$('#param_' + nparam + ' > td > select').attr('data-width', '140px').selectpicker();
        //$('#remove_param_' + nparam).click( function() { remove_last_parameter(); });
	}

	function remove_last_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length - 1;
	    console.log(nparam);
	    if (nparam > 0) {
    	    $('#param_' + nparam).remove();
	    }
    }

	function remove_all_parameters() {
	    var mytable = $("#parameter_list tbody");
	    var nparam = mytable.children().length - 1;
	    for (var i = nparam; i > 0; i--) {
    	    $('#param_' + i).remove();
	    }
    }

	function add_result() {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length;
        var row = '\
            <tr id="result_' + nresult + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_result_' + nresult + '" class="btn btn-default" type="button">\
                                <span class="glyphicon glyphicon-remove"></span>\
                            </button>\
                        </span>\
                        <input class="form-control" style="font-weight: bold;" name="result_name_' + nresult + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="form-control" name="result_default_' + nresult + '" type="text" placeholder="Default value" />\
                        <span class="input-group-btn">\
                            <select name="result_type_' + nresult + '" class="btn btn-default">\
                                <option>text/plain</option>\
                                <option>application/pdf</option>\
                                <option>image/jpeg</option>\
                                <option>image/png</option>\
                                <option>image/fits</option>\
                            </select>\
                        </span>\
                    </div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="form-control" name="result_description_' + nresult + '" type="text" placeholder="Description" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        $(row).insertBefore('#result_list > tbody > tr:last');
        //$('#result_' + nresult + ' > td > select').attr('data-width', '140px').selectpicker();
	}

	function remove_last_result() {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length - 1;
	    if (nresult > 0) {
	        $('#result_' + nresult).remove();
	    }
    }

	function remove_all_results() {
	    var mytable = $("#result_list tbody");
	    var nresult = mytable.children().length - 1;
	    for (var i = nresult; i > 0; i--) {
            $('#result_' + i).remove();
	    }
    }

	function load_wadl() {
        var jobname = $('input[name=name]').val();
        console.log(jobname);
        // ajax command to get_wadl on UWS server
        $.ajax({
			url : '/get_wadl_json/' + jobname, //.split("/").pop(),
			async : true,
			type : 'GET',
			dataType: "json",
			success : function(wadl) {
				$('input[name=executionduration]').val(wadl.executionduration);
				$('textarea[name=description]').val(wadl.description);
				remove_all_parameters();
				var i = 0;
				for (var param in wadl.parameters) {
				    add_parameter();
				    i++;
				    $('input[name=param_name_' + i + ']').val(param);
				    $('select[name=param_type_' + i + ']').val(wadl.parameters[param]['type']);
				    $('input[name=param_default_' + i + ']').val(wadl.parameters[param]['default']);
				    $('input[name=param_required_' + i + ']').prop("checked", wadl.parameters[param]['required'] == "true");
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
			},
			error : function(xhr, status, exception) {
				console.log(exception);
			}
		});
        // ajax command to get_script on UWS server
        $.ajax({
			url : '/get_script/' + jobname, //.split("/").pop(),
			async : true,
			type : 'GET',
			dataType: "text",
			success : function(script) {
				$('textarea[name=script]').val(script);
			},
			error : function(xhr, status, exception) {
				console.log(exception);
			}
		});
    }

	function update_form(json) {
        // given WADL information in json, fill form

    }

	$(document).ready( function() {
        // var myCodeMirror = CodeMirror.fromTextArea($('textarea[name=script]')[0]);
        // Create click functions
        $('#add_parameter').click( function() { add_parameter(); });
        $('#remove_last_parameter').click( function() { remove_last_parameter(); });
        $('#remove_all_parameters').click( function() { remove_all_parameters(); });
        $('#add_result').click( function() { add_result(); });
        $('#remove_last_result').click( function() { remove_last_result(); });
        $('#remove_all_results').click( function() { remove_all_results(); });
        $('#load_wadl').click( function() { load_wadl(); });
	}); // end ready

})(jQuery);