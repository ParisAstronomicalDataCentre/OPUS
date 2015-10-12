( function($) {
	"use strict";

    var editor

	function add_parameter() {
	    var mytable = $("#parameter_list tbody");
	    var iparam = mytable.children().length;
        var row = '\
            <tr id="param_' + iparam + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_param_' + iparam + '" class="btn btn-default" type="button">\
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
                            <select name="param_type_' + iparam + '" class="btn btn-default">\
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
                        <input class="form-control" name="param_description_' + iparam + '" type="text" placeholder="Description" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        $(row).insertBefore('#parameter_list > tbody > tr:last');
        //$('#param_' + iparam + ' > td > select').attr('data-width', '140px').selectpicker();
        $('#remove_param_' + iparam).click( function() {
            iparam = this.id.split('_').pop();
            remove_parameter(iparam);
        });
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
	    for (var i = iparam; i < nparam; i++) {
	        var j = i + 1;
    	    console.log(j + '->' + i);
    	    console.log($('#param_' + j).id);
    	    $('#param_' + j).id = 'param_' + i;
	    }
    }

	function add_result() {
	    var mytable = $("#result_list tbody");
	    var iresult = mytable.children().length;
        var row = '\
            <tr id="result_' + iresult + '">\
                <td>\
                    <div class="input-group input-group-sm col-md-12">\
                        <span class="input-group-btn">\
                            <button id="remove_result_' + iresult + '" class="btn btn-default" type="button">\
                                <span class="glyphicon glyphicon-remove"></span>\
                            </button>\
                        </span>\
                        <input class="form-control" style="font-weight: bold;" name="result_name_' + iresult + '" type="text" placeholder="Name" />\
                        <span class="input-group-addon">=</span>\
                        <input class="form-control" name="result_default_' + iresult + '" type="text" placeholder="Default value" />\
                        <span class="input-group-btn">\
                            <select name="result_type_' + iresult + '" class="btn btn-default">\
                                <option>text/plain</option>\
                                <option>application/pdf</option>\
                                <option>image/jpeg</option>\
                                <option>image/png</option>\
                                <option>image/fits</option>\
                            </select>\
                        </span>\
                    </div>\
                    <div class="input-group input-group-sm col-md-12">\
                        <input class="form-control" name="result_description_' + iresult + '" type="text" placeholder="Description" />\
                    </div>\
                    <div style="height: 8px;"></div>\
                </td>\
            </tr>';
        $(row).insertBefore('#result_list > tbody > tr:last');
        //$('#result_' + iresult + ' > td > select').attr('data-width', '140px').selectpicker();
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
				// $('textarea[name=script]').val(script);
				editor.setValue(script);
			},
			error : function(xhr, status, exception) {
				console.log(exception);
			}
		});
    }

	$(document).ready( function() {
	    editor = CodeMirror.fromTextArea( $('textarea[name=script]')[0], {mode: "text/x-sh", lineNumbers: true } );
        $('div.CodeMirror').addClass('panel panel-default');
        // Create click functions
        $('#add_parameter').click( function() { add_parameter(); });
        $('#remove_last_parameter').click( function() { remove_last_parameter(); });
        $('#remove_all_parameters').click( function() { remove_all_parameters(); });
        $('#add_result').click( function() { add_result(); });
        $('#remove_last_result').click( function() { remove_last_result(); });
        $('#remove_all_results').click( function() { remove_all_results(); });
        $('#load_wadl').click( function() { load_wadl(); });
        // Get jobname from DOM (if set), and update input
        var jobname = $('#jobname').attr('value');
        if (jobname) {
            $('input[name=name]').val(jobname);
            load_wadl();
        };
	}); // end ready

})(jQuery);