/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

( function($) {
	"use strict";

    var editor;  // to use codemirror
    var server_url;
    var server_endpoint;
    var client_endpoint;

    var content_types = [
        'application/octet-stream',
        'text/plain',
        'text/xml',
        'text/x-votable+xml',
        'application/json',
        'application/pdf',
        'application/postscript',
        'image/jpeg',
        'image/png',
        'image/fits',
        'application/x-cdf',
        'video/mp4',
    ];
    var datatype_options = {
        'param': [
            'xs:string',
            'xs:anyURI',
            'xs:float',
            'xs:double',
            'xs:int',
            'xs:long',
            'xs:boolean',
        ],
        'generated': content_types,
        'used': content_types,
    };
    var job_fields = [
        'annotation',
        'doculink',
        'type',
        'subtype',
        'version',
        'contact_name',
        'contact_email',
        'executionDuration',
        'quote',
    ];
    var elt_fields = [
        'name',
        'datatype',
        'type',
        'default',
        'required',
        'annotation',
        'options',
        'attributes',
        'isfile',
        'url',
    ];

    function logger(lvl_name, msg, exception) {
        if (lvl_name == 'DEBUG' && !DEBUG) { return; };
        if (lvl_name == 'OBJECT') { console.log(msg); return; };
        console.log(lvl_name + ' ' + msg);
        if (exception) { console.log(exception); }
    }

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
                $('input[name=name]').typeahead({
                    source: json['jobnames'],
                    autoSelect: false,
                });
                editor.refresh();
            },
            error : function(xhr, status, exception) {
                $('#loading').hide();
                editor.refresh();
                var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
                if (msg && msg.length != 0) {
                    msg = msg[0].replace(/<\/?pre>/g,'');
                }
                logger('ERROR', 'get_jobnames', msg);
                global.showMessage('Cannot get job names from server: ' + msg, 'danger');
                //global.showMessage('Cannot get job names from server', 'danger');
            }
        });
    };

    // ----------
    // Item list numbered

	function item_row(type, ii) {
	    switch (type) {

            // Parameters
            case 'param':
                var options = '<option>' + datatype_options[type].join('</option><option>') + '</option>';
                var row = '\
                    <tr id="param_' + ii + '">\
                        <td>\
                            <div class="input-group input-group-sm col-md-12">\
                                <input class="param_name form-control" style="font-weight: bold;" name="param_name_' + ii + '" type="text" placeholder="Name" />\
                                <span class="input-group-addon">=</span>\
                                <input class="param_default form-control" name="param_default_' + ii + '" type="text" placeholder="Default value" />\
                                <span class="input-group-addon">\
                                    Req.? <input class="param_required" name="param_required_' + ii + '" type="checkbox" title="Required parameter?" checked/>\
                                </span>\
                                <span class="input-group-btn">\
                                    <select class="param_datatype select-small selectpicker" name="param_datatype_' + ii + '">\
                                        ' + options + '\
                                    </select>\
                                </span>\
                                <span class="input-group-btn">\
                                    <button id="moveup_param_' + ii + '" class="moveup_param btn btn-default" type="button" >\
                                        <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="movedown_param_' + ii + '" class="movedown_param btn btn-default" type="button" >\
                                        <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="remove_param_' + ii + '" class="remove_param btn btn-default" type="button" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-remove" aria-hidden="true"></span>\
                                    </button>\
                                </span>\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12" style="width:100%">\
                                <span class="input-group-addon" style="width:70px" title="Description">Desc.</span>\
                                <input class="param_annotation form-control" name="param_annotation_' + ii + '" type="text" placeholder="Description" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" />\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12" style="width:100%">\
                                <span class="input-group-addon" style="width:70px" title="Options">Options</span>\
                                <input class="param_options form-control" name="param_options_' + ii + '" type="text" placeholder="List of possible choices (comma-separated values)" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" />\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12" style="width:100%">\
                                <span class="input-group-addon" style="width:70px" title="Attributes">Attr.</span>\
                                <input class="param_attributes form-control" name="param_attributes_' + ii + '" type="text" placeholder="unit=... ucd=... utype=... min=... max=..." style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" />\
                            </div>\
                            <div style="height: 10px;"></div>\
                        </td>\
                    </tr>';
                break;

            // Used
	        case 'used':
                var options = '<option>' + datatype_options[type].join('</option><option>') + '</option>';
                var row = '\
                    <tr id="used_' + ii + '">\
                        <td>\
                            <div class="input-group input-group-sm col-md-12">\
                                <div class="input-group-sm col-xs-2 nopadding">\
                                    <input class="used_name form-control" style="font-weight: bold;" name="used_name_' + ii + '" type="text" placeholder="Name" />\
                                </div>\
                                <div class="input-group-sm col-xs-1 nopadding">\
                                    <div class="input-group-addon">=</div>\
                                </div>\
                                <div class="input-group-sm col-xs-2 nopadding">\
                                    <input class="used_default form-control" name="used_default_' + ii + '" type="text" placeholder="Default value" />\
                                </div>\
                                <div class="input-group-sm col-xs-1 nopadding">\
                                    <div class="input-group-addon">Mult. </div>\
                                </div>\
                                <div class="input-group-sm col-xs-1 nopadding">\
                                    <input class="used_multiplicity form-control" name="used_multiplicity_' + ii + '" type="text" title="Multiplicity" maxlength="2" />\
                                </div>\
                                <div class="input-group-sm col-xs-5 nopadding">\
                                    <div class="input-group-addon nopadding"></div>\
                                    <div class="input-group-btn">\
                                        <select name="used_contenttype_' + ii + '" class="used_contenttype select-small selectpicker" multiple>\
                                            ' + options + '\
                                        </select>\
                                        <button id="moveup_used_' + ii + '" class="moveup_used btn btn-default" type="button" >\
                                            <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                                        </button>\
                                        <button id="movedown_used_' + ii + '" class="movedown_used btn btn-default" type="button" >\
                                            <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                                        </button>\
                                        <button id="remove_used_' + ii + '" class="remove_used btn btn-default" type="button" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" >\
                                            <span class="glyphicon glyphicon-remove"></span>\
                                        </button>\
                                    </div>\
                                </div>\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12" style="width:100%">\
                                <span class="input-group-addon" style="width:70px" title="Description">Desc.</span>\
                                <input class="used_annotation form-control" name="used_annotation_' + ii + '" type="text" placeholder="Description" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" />\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12" style="width:100%">\
                                <span class="input-group-addon" style="width:70px" title="The input is a File or an ID, possibly with a URL to resolve the ID and download the file (use $ID in the URL template).">\
                                    File <input class="used_isfile" name="used_isfile_' + ii + '" type="radio" value="File" checked/>\
                                    or value  <input class="used_isfile" name="used_isfile_' + ii + '" type="radio" value="value"/>\
                                    or ID  <input class="used_isfile" name="used_isfile_' + ii + '" type="radio" value="ID"/>\
                                    + access URL\
                                </span>\
                                <input class="used_url form-control" name="used_url_' + ii + '" type="text" placeholder="http://url_to_the_input_file?id=$ID" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" />\
                            </div>\
                            <div style="height: 10px;"></div>\
                        </td>\
                    </tr>';
                break;

            // Results
	        case 'generated':
                var options = '<option>' + datatype_options[type].join('</option><option>') + '</option>';
                var row = '\
                    <tr id="generated_' + ii + '">\
                        <td>\
                            <div class="input-group input-group-sm col-md-12">\
                                <input class="generated_name form-control" style="font-weight: bold;" name="generated_name_' + ii + '" type="text" placeholder="Name" />\
                                <span class="input-group-addon">=</span>\
                                <input class="generated_default form-control" name="generated_default_' + ii + '" type="text" placeholder="Default value" />\
                                <span class="input-group-btn">\
                                    <select name="generated_contenttype_' + ii + '" class="generated_contenttype select-small selectpicker">\
                                        ' + options + '\
                                    </select>\
                                </span>\
                                <span class="input-group-btn">\
                                    <button id="moveup_generated_' + ii + '" class="moveup_generated btn btn-default" type="button" >\
                                        <span class="glyphicon glyphicon-arrow-up" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="movedown_generated_' + ii + '" class="movedown_generated btn btn-default" type="button" >\
                                        <span class="glyphicon glyphicon-arrow-down" aria-hidden="true"></span>\
                                    </button>\
                                    <button id="remove_generated_' + ii + '" class="remove_generated btn btn-default" type="button" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" >\
                                        <span class="glyphicon glyphicon-remove"></span>\
                                    </button>\
                                </span>\
                            </div>\
                            <div style="height: 1px;"></div>\
                            <div class="input-group input-group-sm col-md-12" style="width:100%">\
                                <span class="input-group-addon" style="width:70px" title="Description">Desc.</span>\
                                <input class="generated_annotation form-control" name="generated_annotation_' + ii + '" type="text" placeholder="Description" style="border-bottom-right-radius: 4px; border-top-right-radius: 4px;" />\
                            </div>\
                            <div style="height: 10px;"></div>\
                        </td>\
                    </tr>';
                break;
        }
        return row;
	};

	function add_item(type) {
	    var list_table = $('#' + type + '_list tbody');
	    var ii = list_table.children().length + 1;
        // Append row
        var row = item_row(type, ii)
        list_table.append($(row));
        // Initialize selectpicker
        $(".selectpicker").attr('data-width', '120px').selectpicker();
        $(".dropdown-toggle").attr('style', 'border-radius: 0px;')
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
	};

	function reset_item_numbers(type) {
	    var list_table = $('#' + type + '_list > tbody');
        list_table.children().each( function(i) {
            i++;
            if ($(this).attr('id') != type + '_' + i) {
                $(this).attr('id', type + '_' + i);
                $(this).find('.remove_' + type).attr('id', 'remove_' + type + '_' + i);
                $(this).find('.moveup_' + type).attr('id', 'moveup_' + type + '_' + i);
                $(this).find('.movedown_' + type).attr('id', 'movedown_' + type + '_' + i);
                for (var iattr in elt_fields) {
                    var attr = elt_fields[iattr];
                    console.log(attr);
                    console.log(type + '_' + attr + '_' + i);
                    $(this).find('.' + type + '_' + attr).attr('name', type + '_' + attr + '_' + i);
                };
            };
        });
        $('.selectpicker').selectpicker('refresh');
	};

	function move_item_up(type, ii) {
	    var $node = $('#' + type + '_' + ii)
        $node.prev().before($node);
        reset_item_numbers(type);
	};

	function move_item_down(type, ii) {
	    var $node = $('#' + type + '_' + ii)
        $node.next().after($node);
        reset_item_numbers(type);
	};

	function remove_item(type, ii) {
        $('#' + type + '_' + ii).remove();
        reset_item_numbers(type);
    };

	function remove_last_item(type) {
	    var list_table = $('#' + type + '_list tbody');
	    list_table.children().last().remove();
    };

	function remove_all_items(type) {
	    var list_table = $('#' + type + '_list tbody');
	    list_table.children().remove();
    };

    // ----------
    // Load/Read

	function load_jdl() {
        // Load jdl file from sserver and fill jdl_form
        var jobname = $('input[name=name]').val();
        if (jobname.length > 0) {
            $('#loading').show();
            // ajax command to get JDL from UWS server
            $.ajax({
                url: server_url + '/jdl/' + jobname + '/json',  //.split("/").pop(),  // to remove tmp/ (not needed here)
                async: true,
                type: 'GET',
                dataType: "json",
                success: function(jdl) {
                    $('#loading').hide();
                    console.log(jdl);
                    //global.showMessage('JDL loaded.', 'info')
                    //$('#load_msg').attr('class', 'text-info');
                    //$('#load_msg').text('JDL loaded.');
                    //$('#load_msg').show().delay(3000).fadeOut();
                    for (var attr in job_fields) {
                        attr = job_fields[attr];
                        $('[name=' + attr + ']').val(jdl[attr]);
                    };
                    editor.setValue(jdl['script']);
                    editor.refresh();
                    // $('[name=contact_name]').val(jdl.contact_name);
                    // $('[name=contact_email]').val(jdl['contact_email']);
                    // $('[name=executionDuration]').val(jdl.executionDuration);
                    // $('[name=quote]').val(jdl.quote);
                    // $('[name=annotation]').val(jdl.annotation);
                    // Fill param_list table
                    remove_all_items('param');
                    var i = 0;
                    for (var param in jdl.parameters_keys) {
                        param = jdl.parameters_keys[param];
                        add_item('param');
                        i++;  // = jdl.parameters[param]['order'];
                        var attributes = "";
                        var att = ['unit', 'ucd', 'utype', 'min', 'max'];
                        for (var j in att) {
                            var attv = jdl.parameters[param][att[j]]
                            if (attv) {
                                attributes = attributes.concat(att[j] + '=' + new String(attv) + " ");
                            }
                        }
                        var attr_mapping = {
                            'name': param,
                            'datatype': jdl.parameters[param]['datatype'],  //.split(':').pop(),
                            'default': jdl.parameters[param]['default'],
                            'annotation': jdl.parameters[param]['annotation'],
                            'options': jdl.parameters[param]['options'],
                            'attributes': attributes,
                        };
                        for (var attr in attr_mapping) {
                            $('[name=param_' + attr + '_' + i + ']').val(attr_mapping[attr]);
                            console.log(attr_mapping[attr]);
                        }
                        $('input[name=param_required_' + i + ']').prop("checked", jdl.parameters[param]['required'].toString().toLowerCase() == "true");
    //				    $('input[name=param_name_' + i + ']').val(param);
    //				    $('select[name=param_datatype_' + i + ']').val(jdl.parameters[param]['datatype']);
    //				    $('input[name=param_default_' + i + ']').val(jdl.parameters[param]['default']);
    //				    $('input[name=param_annotation_' + i + ']').val(jdl.parameters[param]['annotation']);
    //				    $('input[name=param_options_' + i + ']').val(jdl.parameters[param]['options']);
    //				    $('input[name=param_attributes_' + i + ']').val(attributes);
                    };
                    $('.selectpicker').selectpicker('refresh');
                    // Fill used_list table
                    remove_all_items('used');
                    var i = 0;
                    for (var used in jdl.used_keys) {
                        used = jdl.used_keys[used];
                        add_item('used');
                        i++;
                        var attr_mapping = {
                            'name': used,
                            'contenttype': jdl.used[used]['content_type'],
                            'default': jdl.used[used]['default'],
                            'multiplicity': jdl.used[used]['multiplicity'],
                            'annotation': jdl.used[used]['annotation'],
                        };
                        for (var attr in attr_mapping) {
                            $('[name=used_' + attr + '_' + i + ']').val(attr_mapping[attr]);
                        }
                        // TODO: used_type_ is an array of values (comma separated)
    //				    $('input[name=used_name_' + i + ']').val(used);
    //				    $('select[name=used_type_' + i + ']').val(jdl.used[used]['content_type']);
    //				    $('input[name=used_default_' + i + ']').val(jdl.used[used]['default']);
    //				    $('input[name=used_annotation_' + i + ']').val(jdl.used[used]['annotation']);
                        if (jdl.used[used]['url'].indexOf('file://') == -1) {
                            $('input[name=used_isfile_' + i + '][value=ID]').prop("checked", true);
                            $('input[name=used_url_' + i + ']').val(jdl.used[used]['url']);
                        }
                    };
                    $('.selectpicker').selectpicker('refresh');
                    // Fill generated_list table
                    remove_all_items('generated');
                    var i = 0;
                    for (var result in jdl.generated_keys) {
                        result = jdl.generated_keys[result];
                        add_item('generated');
                        i++;
                        var attr_mapping = {
                            'name': result,
                            'contenttype': jdl.generated[result]['content_type'],
                            'default': jdl.generated[result]['default'],
                            'multiplicity': jdl.generated[result]['multiplicity'],
                            'annotation': jdl.generated[result]['annotation'],
                        };
                        for (var attr in attr_mapping) {
                            $('[name=generated_' + attr + '_' + i + ']').val(attr_mapping[attr]);
                        }
    //				    $('input[name=generated_name_' + i + ']').val(result);
    //				    $('select[name=generated_type_' + i + ']').val(jdl.generated[result]['content_type']);
    //				    $('input[name=generated_default_' + i + ']').val(jdl.generated[result]['default']);
    //				    $('input[name=generated_annotation_' + i + ']').val(jdl.generated[result]['annotation']);
                    };
                    $('.selectpicker').selectpicker('refresh');
                    // ajax command to get_script from UWS server
    //                $.ajax({
    //                    url : server_url + '/jdl/' + jobname + '/script', //.split("/").pop(),
    //                    async : true,
    //                    cache : false,
    //                    type : 'GET',
    //                    dataType: "text",
    //                    success : function(script) {
    //                        // $('textarea[name=script]').val(script);
    //                        editor.setValue(script);
    //                        editor.refresh();
    //                    },
    //                    error : function(xhr, status, exception) {
    //                        editor.setValue('');
    //                        editor.refresh();
    //                        console.log(exception);
    //                        $('#load_msg').attr('class', 'text-danger');
    //                        $('#load_msg').text(exception);
    //                        $('#load_msg').show().delay(2000).fadeOut();
    //                    }
    //                });
                    // Admin can validate this job, unless the form is modified again
                    var jobname = $('input[name=name]').val();
                    if (jobname.indexOf('tmp/') == 0) {
                        $('#validate_jdl').prop('disabled', false);
                    };
                    $("input[name=name]").focus();
                },
                error: function(xhr, status, exception) {
                    $('#loading').hide();
                    editor.setValue('');
                    editor.refresh();
                    var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
                    if (msg && msg.length != 0) {
                        msg = msg[0].replace(/<\/?pre>/g,'');
                    }
                    logger('ERROR', 'load_jdl', msg);
                    global.showMessage('Cannot load JDL: ' + msg, 'danger');
                    //console.log(exception);
                    //global.showMessage(exception, 'danger')
                    //$('#load_msg').attr('class', 'text-danger');
                    //$('#load_msg').text(exception);
                    //$('#load_msg').show().delay(2000).fadeOut();
                }
            });
        } else {
            global.showMessage('No job name given', 'warning');
        };
    };

	function export_jdl() {
        var jobname = $('input[name=name]').val();
        if (jobname.length > 0) {
            if (jobname.search("tmp/") == -1) {
                $('#loading').show();
                // ajax command to get JDL file from UWS server
                $.ajax({
                    url: server_url + '/jdl/' + jobname,  //.split("/").pop(),  // to remove tmp/ (not needed here)
                    type: 'GET',
                    dataType: "text",
                    success: function(response, status, xhr) {
                        // check for a filename
                        var filename = "";
                        var disposition = xhr.getResponseHeader('Content-Disposition');
                        if (disposition && disposition.indexOf('attachment') !== -1) {
                            var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                            var matches = filenameRegex.exec(disposition);
                            if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
                        };
                        var ctype = xhr.getResponseHeader('Content-Type');
                        var blob = new Blob([response], { type: ctype });
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
                    error: function(xhr, status, exception) {
                        $('#loading').hide();
                        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
                        if (msg && msg.length != 0) {
                            msg = msg[0].replace(/<\/?pre>/g,'');
                        }
                        logger('ERROR', 'export_jdl', msg);
                        global.showMessage('Cannot export JDL: ' + msg, 'danger');
                        //console.log(exception);
                        //global.showMessage(exception, 'danger');
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

	function submit_jdl() {
        var jobname = $('input[name=name]').val();
        var csrf_token = $('#csrf_token').attr('value');
        var myForm = document.getElementById('jdl_form');
        var formData = new FormData(myForm);
        formData['script'] = editor.getValue();
        if (jobname.length > 0) {
            $('#loading').show();
            // ajax command to get JDL file from UWS server
            $.ajax({
                url: server_url + '/jdl',
                type: 'POST',
                headers: { "X-CSRFToken": csrf_token },
                data: formData,
                success: function(response, status, xhr) {
                    $('#loading').hide();
                    var jobname = response.jobname;
                    global.showMessage('Job definition has been saved as "tmp/' + jobname + '"', 'success');
                    $('input[name=name]').val('tmp/' + jobname);
                    load_jdl();
                },
                error: function(xhr, status, exception) {
                    $('#loading').hide();
                    var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
                    if (msg && msg.length != 0) {
                        msg = msg[0].replace(/<\/?pre>/g,'');
                    }
                    logger('ERROR', 'submit_jdl', msg);
                    global.showMessage('Cannot submit JDL: ' + msg, 'danger');
                    //console.log(exception);
                    //global.showMessage('Error while submitting job definition', 'danger');
                },
    			processData: false,  // tell jQuery not to process the data
                contentType: false
            });
        } else {
            global.showMessage('No job name given', 'warning');
        };
	};

	function import_jdl() {
        var fname = $('input[name=jdl_file]').val();
        var csrf_token = $('#csrf_token').attr('value');
        var myForm = document.getElementById('import_jdl');
        var formData = new FormData(myForm);
        if (fname.length > 0) {
            $('#loading').show();
            // ajax command to get JDL file from UWS server
            $.ajax({
                url: server_url + '/jdl/import_jdl',
                type: 'POST',
                headers: { "X-CSRFToken": csrf_token },
                data: formData,
                success: function(response, status, xhr) {
                    $('#loading').hide();
                    var jobname = response.jobname;
                    global.showMessage('Job definition has been successfully imported as "tmp/' + jobname + '"',
                    'success');
                    $('input[name=name]').val('tmp/' + jobname);
                    load_jdl();
                },
                error: function(xhr, status, exception) {
                    $('#loading').hide();
                    var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
                    if (msg && msg.length != 0) {
                        msg = msg[0].replace(/<\/?pre>/g,'');
                    }
                    logger('ERROR', 'import_jdl', msg);
                    global.showMessage('Cannot import JDL file (check that JDL file is valid): ' + msg, 'danger');
                },
    			processData: false,  // tell jQuery not to process the data
                contentType: false
            });
        } else {
            global.showMessage('No file selected', 'warning');
        };
	};

	function validate_jdl() {
        var jobname = $('input[name=name]').val();  //.split("/").pop();  // remove 'tmp/'
        var csrf_token = $('#csrf_token').attr('value');
        if (jobname.length > 0) {
            if (jobname.indexOf('tmp/') == 0) {
                $('#loading').show();
                // ajax command to get JDL file from UWS server
                $.ajax({
                    url: server_url + '/jdl/' + jobname + '/validate',
                    type: 'POST',
                    headers: { "X-CSRFToken": csrf_token },
                    success: function(response, status, xhr) {
                        $('#loading').hide();
                        var jobname = response.jobname;
                        global.showMessage('Job definition for "tmp/' + jobname + '" has been successfully validated and \
                        renamed "' + jobname + '"', 'success');
                        $('input[name=name]').val(jobname);
                        load_jdl();
                        $("#validate_jdl").prop("disabled", true);
                    },
                    error: function(xhr, status, exception) {
                        $('#loading').hide();
                        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
                        if (msg && msg.length != 0) {
                            msg = msg[0].replace(/<\/?pre>/g,'');
                        }
                        logger('ERROR', 'validate_jdl', msg);
                        global.showMessage('Cannot validate JDL file: ' + msg, 'danger');
                    },
                    processData: false,  // tell jQuery not to process the data
                    contentType: false
                });
            } else {
                global.showMessage('Job definition needs to start with "tmp/". Please submit form before validation.',
                'warning');
            };
        } else {
            global.showMessage('No job name given', 'warning');
        };
	};

    // ----------
    // ready()

	$(document).ready( function() {
        server_url = $('#server_url').attr('value');
        server_endpoint = $('#server_endpoint').attr('value');
        client_endpoint = $('#client_endpoint').attr('value');
        get_jobnames();
	    // Script editor with CodeMirror
	    editor = CodeMirror.fromTextArea( $('textarea[name=script]')[0], {mode: "text/x-sh", lineNumbers: true } );
        $('div.CodeMirror').addClass('panel panel-default');
        // Prepare empty form
        // add_item('param');
        // add_item('generated');
        // Get jobname from DOM (if set), and fill input form
        var jobname = $('#jobname').attr('value');
        if (jobname) {
            $('input[name=name]').val(jobname);
            load_jdl();
        };
        // Add event functions
        $('#import_jdl').submit( function(event) {
            event.preventDefault();
            import_jdl();
        });
        $('#load_jdl').click( function() {
            var jobname = $('input[name=name]').val();
            if (jobname.indexOf('tmp/') == 0) {
                setTimeout(function(){ $("#validate_jdl").prop("disabled", false); }, 200);
            };
            load_jdl();
        });
        $('#export_jdl').click( function() {
            export_jdl();
        });
        $('#jdl_form').submit( function(event) {
            event.preventDefault();
            submit_jdl();
        });
        $('#submit_jdl').click( function() {
            $('#jdl_form_submit').click();
        });
        $('#validate_jdl').click( function() {
            validate_jdl();
        });
        // Internal form buttons
        $('#add_parameter').click( function() {
            add_item('param');
        });
        $('#remove_all_parameters').click( function() {
            remove_all_items('param');
        });
        $('#add_used').click( function() {
            add_item('used');
        });
        $('#remove_all_used').click( function() {
            remove_all_items('used');
        });
        $('#add_generated').click( function() {
            add_item('generated');
        });
        $('#remove_all_generateds').click( function() {
            remove_all_items('generated');
        });
        // Load JDL on return keydown for job name
        $('input[name=name]').keydown( function (event) {
            if (event.keyCode == 13) {
                //$('.ui-autocomplete').hide();
                event.preventDefault();
                setTimeout(function(){load_jdl();}, 200);
            };
        });
        $("input[name=name]").focusout( function() {
            setTimeout(function(){ $("#validate_jdl").prop("disabled", true); }, 200);
        });
	}); // end ready

})(jQuery);