/*!
 * UWS Client
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

// The client fills a Job List table with id=job_list
// <table id="job_list" class="table table-bordered table-striped table-condensed"></table>

// It can also show the job parameters located in form inputs with id=id_*

// The properties are listed in a table with id=prop_list
// <table id='prop_list' class="table table-bordered table-striped table-condensed"></table>

// The results are shown as bootstrap panels in a div block with id=results_list
// <div id='results_list' class='text-center'></div>

// Some results (stdout, stderr, provxml, provsvg) are shown as bootstrap panels in a div block with id=details_list
// <div id='details_list' class='text-center'></div>

var uws_client = (function($) {
    "use strict";

    // Config
    var DEBUG = true;
    var host_root = location.protocol + '//' + location.host;
    var server_endpoint_jobs = '/rest';
    var server_endpoint_jdl = '/jdl/<jobname>/json';
    var server_endpoint_results = '/store';
    var client_endpoint = '/opus_client';
    var client_endpoint_jdl = '/jdl';
    var client_endpoint_jobs = '/jobs';
    var client_endpoint_job_edit = '/job_edit';
    var client_endpoint_job_form = '/job_form';
    var client_endpoint_proxy = '/proxy';

    var job_list_columns = [
        //'jobName',  // job.jobName
        'jobId',  // job.jobId
        'runId',  // job.runId
        'creationTime',
        'phase',
        'details',
        //'edit',
        //'results',
        'control',
        //'delete',
        //'ownerId',
    ];
    var job_list_column_names = {
        jobName: 'Job Name',
        jobId: 'jobId',
        runId: 'runId',
        ownerId: 'Owner',
        creationTime: 'Creation Time',
        phase: 'Phase',
        edit: 'Edit Job',
        details: 'Details',
        results: 'Results',
        control: 'Control',
        delete: 'Delete',
    };
    var job_list_columns_nosort = ['details', 'edit', 'results', 'control', 'delete']

    // Internal
    var jobNames;
    var clients = {};
    var refreshPhaseTimeout = {}; // stores setInterval functions for phase refresh
    var refreshPhaseTimeoutDelay = {}; //
    var timeoutDelays = [2000,2000,3000,4000,5000]; // delays in ms
    var selectedJobId;

    if (!('global' in window)) {
        // console.log('Redefine global');
        var global = {};
    } else {
        //console.log('Use window.global');
        var global = window.global;
    };
    if (!('showMessage' in global)) {
        // console.log('Redefine global functions');
        var fadeOutAll = function () {
            $('.fadeOut').delay(3000).fadeOut(2000);
        };
        global.fadeOutAll = fadeOutAll;
        var showMessage = function (msg, category) {
            if (category.length == 0) {
                category = 'info';
            }
            $("#messages").append('<div class="fadeOut alert alert-' + category + ' text-center">' + msg + '</div>');
            fadeOutAll();
        };
        global.showMessage = showMessage;
    }

    //----------
    // LOGGER (show info in console or other logger)

    function logger(lvl_name, msg, exception) {
        if (lvl_name == 'DEBUG' && !DEBUG) { return; };
        if (lvl_name == 'OBJECT') { console.log(msg); return; };
        console.log(lvl_name + ' ' + msg);
        if (exception) { console.log(exception); }
    }


    //----------
    // Scroll to an anchor in the page with slow animation

    function scrollToAnchor(aid){
        var elt = $("#"+ aid);
        if (elt.length != 0) {
            $('html,body').animate( {scrollTop: elt.offset().top}, 'slow' );
        }
    }

    $.event.special.destroyed = {
        remove: function(o) {
                if (o.handler) {
                    o.handler()
            }
        }
    }


    //----------
    // CREATE MANAGER AND CLIENTS

    function initClient(serviceUrl, serverEndpoint, clientEndpoint, jobNames_init, set_job_list_columns=[]){
        jobNames = jobNames_init;
        if (set_job_list_columns.length) {
            job_list_columns = set_job_list_columns;
        };
        if (serverEndpoint.length) {
            server_endpoint_jobs = serverEndpoint;
        };
        if (clientEndpoint.length) {
            client_endpoint = clientEndpoint;
        };
        for (var i in jobNames) {
            // Init client
            var url = serviceUrl + server_endpoint_jobs + '/' + jobNames[i];
            clients[jobNames[i]] = new uwsLib.uwsClient(url);
            // Get JDL for job
            $.getJSON(serviceUrl + server_endpoint_jdl.replace("<jobname>", jobNames[i]), function(jdl) {
                clients[jobNames[i]].jdl = jdl;
            });
            logger('INFO', 'uwsClient at ' + clients[jobNames[i]].serviceUrl);
        };
    };

    function wait_for_jdl(jobName, next_function, args){
        if ((typeof clients[jobName] !== "undefined") && (typeof clients[jobName].jdl !== "undefined")) {
            logger('DEBUG', 'JDL set for ' + jobName);
            logger('OBJECT', clients[jobName].jdl);
            next_function.apply(this, args);
        } else {
            logger('DEBUG', 'Wait for JDL for ' + jobName);
            setTimeout(function(){
                wait_for_jdl(jobName, next_function, args);
            }, 500);
        };
    }


    //----------
    // PREPARE TABLE

    var prepareTable = function() {
        $('#job_list').attr('class', 'table table-bordered table-condensed');
        var tcontent = '\
            <thead>\
                <tr>';
        for (var col in job_list_columns) {
            var col_code = job_list_columns[col];
            var col_name = job_list_column_names[col_code];
            var col_class = 'text-center';
            if (job_list_columns_nosort.indexOf(col_code) != -1) {
                col_class += ' sorter-false';
            };
            if (col_code == 'creationTime') {
                col_class += ' sorter-shortDate dateFormat-yyyymmdd';
            };
            tcontent = tcontent + '\
                    <th id="' + col_code + '" class="' + col_class + '">' + col_name + '</th>';
        };
        tcontent = tcontent + '\
                </tr>\
            </thead>\
            <tbody>\
            </tbody>';
        tcontent = tcontent + '\
            <tfoot>\
                <tr>\
                  <th colspan="' + job_list_columns.length + '" class="ts-pager form-inline">\
                    <div class="btn-group btn-group-sm" role="group">\
                      <button type="button" class="btn btn-default first"><span class="glyphicon glyphicon-step-backward"></span></button>\
                      <button type="button" class="btn btn-default prev"><span class="glyphicon glyphicon-backward"></span></button>\
                    </div>\
                    <span class="pagedisplay"></span>\
                    <div class="btn-group btn-group-sm" role="group">\
                      <button type="button" class="btn btn-default next"><span class="glyphicon glyphicon-forward"></span></button>\
                      <button type="button" class="btn btn-default last"><span class="glyphicon glyphicon-step-forward"></span></button>\
                    </div>\
                    <select class="form-control input-sm pagesize" title="Select page size">\
                      <option value="10">10</option>\
                      <option selected="selected" value="20">20</option>\
                      <option value="30">30</option>\
                      <option value="all">All Rows</option>\
                    </select>\
                    <select class="form-control input-sm pagenum" title="Select page number"></select>\
                  </th>\
                </tr>\
            </tfoot>';
        $('#job_list').html(tcontent);
    };


    //----------
    // SELECT JOB

    var selectJob = function(jobId) {
        $('#job_list tbody').find('tr.bg-info').removeClass('bg-info');
        $('#'+jobId).addClass("bg-info");
    }



    //----------
    // DISPLAY functions
    //----------


    //----------
    // DISPLAY PHASE

    var displayPhase = function(jobId, phase) {
        var phase_class = 'btn-default';
        var phase_icon = '';
        $('#'+jobId+' td button.results').attr("disabled", "disabled");
        $('#'+jobId+' td button.start').attr("disabled", "disabled");
        $('#'+jobId+' td button.abort').attr("disabled", "disabled");
        switch (phase) {
            case 'PENDING':
                phase_class = 'btn-warning';
                $('#'+jobId+' td button.start').removeAttr("disabled");
                break;
            case 'QUEUED':
                phase_class = 'btn-info';
                $('#'+jobId+' td button.abort').removeAttr("disabled");
                phase_icon = '<span class="glyphicon glyphicon-refresh glyphicon-refresh-animate"></span>&nbsp;';
                break;
            case 'EXECUTING':
                phase_class = 'btn-primary';
                $('#'+jobId+' td button.abort').removeAttr("disabled");
                phase_icon = '<span class="glyphicon glyphicon-refresh glyphicon-refresh-animate"></span>&nbsp;';
                break;
            case 'COMPLETED':
                phase_class = 'btn-success';
                $('#'+jobId+' td button.results').removeAttr("disabled");
                break;
            case 'ERROR':
                phase_class = 'btn-danger';
                $('#'+jobId+' td button.results').removeAttr("disabled");
                break;
            case 'ABORTED':
                phase_class = 'btn-danger';
                $('#'+jobId+' td button.results').removeAttr("disabled");
                break;
            case 'UNKNOWN':
                phase_class = 'btn-danger';
                $('#'+jobId+' td button.abort').removeAttr("disabled");
                phase_icon = '<span class="glyphicon glyphicon-refresh glyphicon-refresh-animate"></span>&nbsp;';
                break;
            case 'HELD':
                phase_class = 'btn-default';
                $('#'+jobId+' td button.abort').removeAttr("disabled");
                $('#'+jobId+' td button.start').removeAttr("disabled");
                break;
            case 'SUSPENDED':
                phase_class = 'btn-default';
                $('#'+jobId+' td button.abort').removeAttr("disabled");
                phase_icon = '<span class="glyphicon glyphicon-refresh glyphicon-refresh-animate"></span>&nbsp;';
                break;
        };
        $('#'+jobId+' td button.phase').html(phase_icon + phase);
        $('#'+jobId+' td button.phase').removeClass( function (index, css) {
            return (css.match(/(^|\s)btn-\S+/g) || []).join(' ');
        });
        $('#'+jobId+' td button.phase').addClass(phase_class);
        // Refresh phase if change is expected
        switch (phase) {
            case 'QUEUED':
            case 'EXECUTING':
            case 'UNKNOWN':
            case 'SUSPENDED':
                refreshPhaseTimeout[jobId] = setTimeout(getJobPhase, refreshPhaseTimeoutDelay[jobId], jobId);
        };
    };


    //----------
    // REFRESH PHASE

    var refreshPhase = function(jobId, phase) {
        // Display PHASE button
        displayPhase(jobId, phase);
        // Display properties in table prop_list
        if ($("#prop_list").length) {
            refreshProps(jobId);
        };
        if (phase != 'PENDING') {
            // Set parameter inputs to readonly
            if ($("#job_params").length) {
                $('[id^=id_]').attr('readonly','readonly');
                $('[id^=button_]').attr('disabled','disabled');
            };
        };
        // Display results as panels in div results
        if ($("#results_list").length) {
            refreshResults(jobId);
        };
        if (phase == 'COMPLETED') {
            logger('INFO', 'Job completed '+jobId);
        };
    };


    //----------
    // DISPLAY JOB ROW

    var displayJobRow = function(job){
        logger('OBJECT', job);
        var creation_time = job.creationTime;  //.split("T");
        if (creation_time.length == 1) {
            creation_time = "";
        //} else {
        //    creation_time = creation_time[0]+' '+creation_time[1].split('+')[0];
        };
        var times = '';
        var param_list = '';
//        var start_time = job.startTime.split("T");
//        if (start_time.length == 1) {
//            start_time = "";
//        } else {
//            start_time = start_time[0]+' '+start_time[1].split('+')[0];
//        };
//        var end_time = job.endTime.split("T");
//        if (end_time.length == 1) {
//            end_time = "";
//        } else {
//            end_time = end_time[0]+' '+end_time[1].split('+')[0];
//        };
//        var destr_time = job.destruction.split("T");
//        if (destr_time.length == 1) {
//            destr_time = "";
//        } else {
//            destr_time = destr_time[0]+' '+destr_time[1].split('+')[0];
//        };
//        var times = 'creation:    \t'+creation_time+'\n'+'start:         \t'+start_time+'\n'+'end:           \t'+end_time+'\n'+'destruction:\t'+destr_time
//        var param_list = "jobid = " + job.jobId + '\nParameters:';
//        for (var pname in job.parameters) {
//            var pvalue = job.parameters[pname].value;
//            pvalue = decodeURIComponent(pvalue).replace(/[+]/g, " ");
//            param_list += '\n' + pname + ' = ' + pvalue;
//        };

        var row = '<tr id='+ job.jobId +' jobname='+ job.jobName +'>';
        var col_content = {
            jobName: '<td class="text-center" style="vertical-align: middle;" title="' + param_list + '">' + job.jobName + '</td>',
            jobId: '<td class="text-center" style="vertical-align: middle;">' + job.jobId + '</td>',
            runId: '<td class="text-center" style="vertical-align: middle;">' + job.runId + '</td>',
            ownerId: '<td class="text-center" style="vertical-align: middle;">' + job.ownerId + '</td>',
            creationTime: '<td class="text-center" style="vertical-align: middle;" title="' + times + '">' + creation_time + '</td>',
            phase: '\
                <td class="text-center" style="vertical-align: middle;">\
                    <button type="button" class="phase btn btn-default">PHASE...</button>\
                </td>',
            edit: '\
                <td class="text-center" style="vertical-align: middle;">\
                    <button type="button" class="properties btn btn-default btn-sm" title="Edit">\
                        <span class="glyphicon glyphicon-info-sign"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Edit Job</span>\
                    </button>\
                </td>',
            details: '\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="btn-group">\
                        <button type="button" class="properties btn btn-default btn-sm" title="Properties">\
                            <span class="glyphicon glyphicon-info-sign"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;Properties</span>\
                        </button>\
                        <button type="button" class="parameters btn btn-default btn-sm" title="Parameters">\
                            <span class="glyphicon glyphicon-edit"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;&nbsp;Parameters</span>\
                        </button>\
                        <button type="button" class="results btn btn-default btn-sm" title="Results">\
                            <span class="glyphicon glyphicon-save"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;Results</span>\
                        </button>\
                    </div>\
                </td>',
            results: '\
                <td class="text-center" style="vertical-align: middle;">\
                    <button type="button" class="results btn btn-default btn-sm" title="Results">\
                        <span class="glyphicon glyphicon-save"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Results</span>\
                    </button>\
                </td>',
            control: '\
                <td class="text-center" style="vertical-align: middle;">\
                    <div class="btn-group">\
                        <button type="button" class="start btn btn-default btn-sm" title="Start">\
                            <span class="glyphicon glyphicon-play"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;Start</span>\
                        </button>\
                        <button type="button" class="log btn btn-default btn-sm" title="Get current log">\
                            <span class="glyphicon glyphicon-question-sign"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;Start</span>\
                        </button>\
                        <button type="button" class="abort btn btn-default btn-sm" title="Abort">\
                            <span class="glyphicon glyphicon-off"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;Abort</span>\
                        </button>\
                        <button type="button" class="delete btn btn-default btn-sm" title="Delete">\
                            <span class="glyphicon glyphicon-trash"></span>\
                            <span class="hidden-xs hidden-sm hidden-md hidden-lg">&nbsp;Delete</span>\
                        </button>\
                    </div>\
                </td>',
            delete: '\
                <td class="text-center" style="vertical-align: middle;">\
                    <button type="button" class="delete btn btn-default btn-sm" title="Delete">\
                        <span class="glyphicon glyphicon-trash"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Delete</span>\
                    </button>\
                </td>',
        };
        for (var col in job_list_columns) {
            var col_code = job_list_columns[col];
            row = row + col_content[col_code];
        };
        var col_code = 'ownerId';
        var col_name = job_list_column_names[col_code];
        if ($.inArray(col_code, job_list_columns) == -1) {
            if (job.ownerId.length > 0) {
                var headers = [];
                $('#job_list > thead > tr > th').each(function(){
                    headers.push($(this).text());
                });
                if ($.inArray(col_name, headers) == -1) {
                    logger('INFO', 'Adding Owner column');
                    // Add column 'Owner', add 'ownerId' to job_list_columns
                    job_list_columns.push(col_code);
                    $('#job_list > thead > tr').append('<<th id="' + col_code +'" class="text-center">' + col_name +
                    '</th>');
                };
                row = row + col_content[col_code];
            };
        };
        row = row + '</tr>';
//        var row = '\
//            <tr id='+ job.jobId +' jobname='+ job.jobName +'>\
//                <td class="text-center" style="vertical-align: middle;" title="' + param_list + '">' + job.jobName + '</td>\
//                <td class="text-center" style="vertical-align: middle;">' + job.runId + '</td>\
//                <td class="text-center" style="vertical-align: middle;" title="' + times + '">' + creation_time + '</td>\
//                <td class="text-center" style="vertical-align: middle;">\
//                    <button type="button" class="phase btn btn-default">PHASE...</button>\
//                </td>\
//                <td class="text-center" style="vertical-align: middle;">\
//                    <div class="btn-group">\
//                        <button type="button" class="properties btn btn-default btn-sm">\
//                            <span class="glyphicon glyphicon-info-sign"></span>\
//                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Properties</span>\
//                        </button>\
//                        <button type="button" class="parameters btn btn-default btn-sm">\
//                            <span class="glyphicon glyphicon-edit"></span>\
//                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;&nbsp;Parameters</span>\
//                        </button>\
//                        <button type="button" class="results btn btn-default btn-sm">\
//                            <span class="glyphicon glyphicon-save"></span>\
//                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Results</span>\
//                        </button>\
//                    </div>\
//                </td>\
//                <td class="text-center" style="vertical-align: middle;">\
//                    <div class="btn-group">\
//                        <button type="button" class="start btn btn-default btn-sm">\
//                            <span class="glyphicon glyphicon-play"></span>\
//                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Start</span>\
//                        </button>\
//                        <button type="button" class="abort btn btn-default btn-sm">\
//                            <span class="glyphicon glyphicon-off"></span>\
//                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Abort</span>\
//                        </button>\
//                        <button type="button" class="delete btn btn-default btn-sm">\
//                            <span class="glyphicon glyphicon-trash"></span>\
//                            <span class="hidden-xs hidden-sm hidden-md">&nbsp;Delete</span>\
//                        </button>\
//                    </div>\
//                </td>\
//            </tr>';
        // Insert row in table
        $('#job_list tbody').prepend(row);
        // Display phase according to phase status, and update on click
        displayPhase(job.jobId, job.phase);
        // Refresh phase button
        $('#'+job.jobId+' td button.phase').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            getJobPhase(jobId);
        });
        // Start job button
        $('#'+job.jobId+' td button.start').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            startJob(jobId);
        });
        // Get log button
        $('#'+job.jobId+' td button.log').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            var logURL = clients[jobName].serviceUrl + "/" + jobId + "/stdout"
            window.open(logURL, "_blank", "width=800, height=400");
        });
        // Abort job button
        $('#'+job.jobId+' td button.abort').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var isOk = window.confirm("Abort job\nAre you sure?");
            if (isOk) {
                abortJob(jobId);
            };
        });
        // Delete job button
        $('#'+job.jobId+' td button.delete').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var isOk = window.confirm("Delete job\nAre you sure?");
            if (isOk) {
                destroyJob(jobId);
            };
        });
    };


    //----------
    // DISPLAY JOB

    var displayJob = function(job){
        // Display row
        displayJobRow(job);
        // Events for Details buttons
        $('#'+job.jobId+' td button.properties').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            selectJob(jobId);
            window.location.href = client_endpoint + client_endpoint_job_edit + "/" + jobName + "/" + jobId + '#properties';
        });
        $('#'+job.jobId+' td button.parameters').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            selectJob(jobId);
            window.location.href = client_endpoint + client_endpoint_job_edit + "/" + jobName + "/" + jobId + '#parameters';
        });
         $('#'+job.jobId+' td button.results').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            selectJob(jobId);
            window.location.href = client_endpoint + client_endpoint_job_edit + "/" + jobName + "/" + jobId + '#results';
        });
    };


    //----------
    // DISPLAY PROPS

    var displayProps = function(job){
        for (var p in job) {
            if (job[p]) {
                switch (p) {
                    case 'parameters':
                    case 'results':
//                        var res_str = '<tr><td><strong>'+p+'</strong></td><td>';
//                        for (var res in job[p]) {
//                            res_str += res+': '+decodeURIComponent(job[p][res])+'<br/>';
//                        };
//                        $('#prop_list').append(res_str+'</td></tr>');
                        break;
                    default:
                        $('#prop_list').append('<tr><td><strong>'+p+'</strong></td><td>'+job[p]+'</td></tr>');
                };
            };
        };
    };


    //----------
    // DISPLAY PARAMS (as forms)

    var displayParamFormInput = function(pname, p){
        var phide = ''
        var pclass = 'form-group'
        if (p.required == 'false') { //.toLowerCase()
            phide = ' style="display:none; color:grey"';
            pclass = 'form-group optional';
        };
        var row = '\
            <div class="' + pclass + '"' + phide + '>\
                <label class="col-md-3 control-label">' + pname + '</label>\
                <div id="div_' + pname + '" class="col-md-5 controls">\
                    <input class="form-control" id="id_' + pname + '" name="' + pname + '" type="text" value="' + p.default + '"/>\
                </div>\
                <div class="col-md-4 help-block">\
                    ' + p.annotation + '\
                </div>\
            </div>';
        if (p.control == 'true') {
            if ($('#add_control').length) {
                $('#add_control').before(row);
            } else {
                $('#job_params').append(row);
            };
            $('#id_'+pname).wrap('<div class="input-group"></div>');
            // Add remove button
            $('#id_'+pname).parent().append('\
                <span class="input-group-btn">\
                    <button id="button_'+pname+'" class="btn btn-default" type="button" title="Remove item">\
                        <span class="glyphicon glyphicon-remove"></span>\
                    </button>\
                </span>');
            // Add event
            $('#button_'+pname).click( function() {
                $('#div_'+pname).parent().remove();
            });
        } else {
            $('#job_params').append(row);
        };
    };
    var displayParamFormInputType = function(pname, p){
        if (p.datatype == 'file'  || p.url == 'file://$ID') {
            $('#id_'+pname).attr('type', 'file');
            $('#id_'+pname).wrap('<div class="input-group"></div>');
            $('#id_'+pname).parent().append('\
                <span class="input-group-btn">\
                    <button id="button_'+pname+'" class="btn btn-default" type="button" title="Remove item">\
                        File <span class="glyphicon glyphicon-transfer"></span> URL\
                    </button>\
                </span>');
            $('#button_'+pname).click( function() {
                if ($('#id_'+pname).attr('type') == 'file') {
                    $('#id_'+pname).attr('type', 'url');
                } else {
                    $('#id_'+pname).attr('type', 'file');
                };
            });
        };
        if ((p.datatype.indexOf('long') > -1)
            || (p.datatype.indexOf('int') > -1)
            || (p.datatype.indexOf('float') > -1)
            || (p.datatype.indexOf('double') > -1)) {
            $('#id_'+pname).attr('type', 'number');
            $('#id_'+pname).attr('step', 'any');
            if (p.min) {
                $('#id_'+pname).attr('min', p.min);
            };
            if (p.max) {
                $('#id_'+pname).attr('max', p.max);
            };
        };
        if (p.datatype.indexOf('anyURI') > -1) {
            $('#id_'+pname).attr('type', 'url');
        };
        if (p.datatype.indexOf('bool') > -1) {
            // Change to checkbox
            $('#id_'+pname).removeClass('form-control');
            $('#id_'+pname).attr('type', 'checkbox');
            $('#id_'+pname).wrap('<div class="checkbox"></div>');
            $('#id_'+pname).attr('style', 'margin-left: 10px;');
            var val = p.default //.toLowerCase();
            if ((val == 'true') || (val == 'yes')) {
                $('#id_'+pname).attr('checked', 'checked');
            };
        };
        if (p.options) {
            // change input to select and run selectpicker
            logger('DEBUG', 'Change text input to select input with limited options');
            var elt = '\
                <select class="selectpicker" id="id_' + pname + '" name="' + pname + '">\n\
                </select>\n';

            $('#id_'+pname).replaceWith(elt);
            var options = p.options.split(',');
            for (var i in options) {
                $('#id_'+pname).append('<option>' + options[i] + '</option>');
                $('select[name=' + pname + ']').attr('data-width', '100%').selectpicker();
                $('select[name=' + pname + ']').val(p.default);
            };
            $('.selectpicker').selectpicker('refresh');
        };
    };
    var displayParamFormOk = function(jobName, init_params){
        $('#loading').hide();
        // Run displayParamForm before to check that jdl is defined
        var jdl = clients[jobName].jdl;
        // First field is the runId
        if (jdl.control_parameters_keys.indexOf('runId') > -1) {
            displayParamFormInput('runId', {'default': jobName, 'annotation': 'User specific identifier for the job', 'control': 'true'});
        };
        $('#job_params').append('<hr>');
        // Create form fields from JDL
        for (var pkey in jdl.used_keys) {
            var pname = jdl.used_keys[pkey];
            // Add form input if pname is not a parameter already
            if ($.inArray(pname, Object.keys(jdl.parameters)) == -1) {
                var p = jdl.used[pname];
                displayParamFormInput(pname, p)
                displayParamFormInputType(pname, p)
            };
        };
        $('#job_params').append('<hr>');
        for (var pkey in jdl.parameters_keys) {
            var pname = jdl.parameters_keys[pkey];
            if ($('#id_' + pname).length == 0) {
                var p = jdl.parameters[pname];
                displayParamFormInput(pname, p)
                displayParamFormInputType(pname, p)
            };
        };
        // Fill with init_params
        for(var pname in init_params){
            if (init_params.hasOwnProperty(pname)){
                var pvalue = init_params[pname];
                // work with key and value
                pvalue = decodeURIComponent(pvalue).replace(/[+]/g, " ");
                // Add control parameter (it does not exist previously)
                if ($('#id_' + pname).length == 0) {
                    var pdesc = jdl.control_parameters[pname];
                    displayParamFormInput(pname, {'default': '', 'annotation': pdesc, 'control': 'true'})
                };
                // Update form fields
                $('#id_' + pname).attr('value', pvalue);
                // If type=file, and url is given, then switch type to urk
                if ($('#id_'+pname).attr('type') == 'file' && pvalue.indexOf('http') !== -1) {
                    $('#id_'+pname).attr('type', 'url');
                };
            };
        };
        // Add buttons
        $('#job_params').append('<hr>');
        var elt = '\
            <div id="add_control" class=" form-group">\n\
                <label class="col-md-3 control-label">Add control parameters</label>\n\
                <div class="col-md-5 controls">\n\
                    <select id="control_parameters" name="control_parameters" class="selectpicker" title="Chose parameter" data-width="100%">\n\
                        <option data-hidden="true"></option>\n\
                    </select>\n\
                </div>\n\
            </div>\n\
            <div id="form-buttons" class="form-group">\n\
                <div class="col-md-offset-3 col-md-9">\n\
                    <button type="submit" class="btn btn-primary">Submit</button>\n\
                    <button type="reset" class="btn btn-default">Reset</button>\n\
                    <button id="showopt" type="button" class="btn btn-default">Show optional parameters</button>\n\
                </div>\n\
            </div>\n';
        $('#job_params').append(elt);
        // Add options to control parameters dropdown
        for (var pkey in jdl.control_parameters_keys) {
            var pname = jdl.control_parameters_keys[pkey];
            $('#control_parameters').append('<option value="' + pname + '">' + pname + '</option>');
        };
        $('.selectpicker').selectpicker('refresh');
        // Event to add control parameter
        $('#control_parameters').on('changed.bs.select', function(){
            var pname = $('#control_parameters').val();
            if ($('#id_' + pname).length == 0) {
                var pdesc = jdl.control_parameters[pname];
                displayParamFormInput(pname, {'default': '', 'annotation': pdesc, 'control': 'true'})
            } else {
                $('#id_' + pname).focus();
            };
        });
        // Event to show optional parameters
        $('#showopt').click( function() {
            var btext = $('#showopt').html();
            if (btext.indexOf('Show') > -1) {
                $('.optional').show();
                $('#showopt').html("Hide optional parameters");
            } else {
                $('.optional').hide();
                $('#showopt').html("Show optional parameters");
            };
        });
    };
    var displayParamFormOkFilled = function(job){
        $('#loading').hide();
        var jdl = clients[job.jobName].jdl;
        // Create form fields from JDL
        // list all used entities
        for (var pkey in jdl.used_keys) {
            var pname = jdl.used_keys[pkey];
            if ($.inArray(pname, Object.keys(jdl.parameters)) == -1) {
                var p = jdl.used[pname];
                displayParamFormInput(pname, p);
                if (p.url != 'file://$ID') {
                    $('#id_'+pname).wrap('<div class="input-group"></div>');
                    // Add Update buttons (possible to update params when pĥase is PENDING in UWS 1.0 - but not yet implemented)
                    $('#id_'+pname).parent().append('<span class="input-group-btn"><button id="button_'+pname+'" class="btn btn-default" type="button">Update</button></span>');
                    // Change input type
                    displayParamFormInputType(pname, p);
                } else {
                    // param is a file, but only a text is shown
                    $('#id_'+pname).attr('disabled','disabled');
                    if (!(pname in job.parameters)) {
                        $('#id_'+pname).wrap('<div class="input-group"></div>');
                        $('#id_'+pname).parent().append('<span class="input-group-addon" style="line-height: 1.4;"><small>default used</small></span>');
                    };
                };
                // Change right corners for checkbox and select inside input-group
                if (p.datatype.indexOf('bool') > -1) {
                    $('#id_'+pname).parent().attr('style','border-bottom-right-radius: 0px; border-top-right-radius: 0px;');
                };
                if (p.options) {
                    $('button[data-id=id_'+pname+']').attr('style','border-bottom-right-radius: 0px; border-top-right-radius: 0px; opacity: 1;');
                };
            }
        };
        // list remaining parameters from JDL
        for (var pkey in jdl.parameters_keys) {
            var pname = jdl.parameters_keys[pkey];
            var p = jdl.parameters[pname];
            displayParamFormInput(pname, p);
            if (p.datatype != 'file') {
                $('#id_'+pname).wrap('<div class="input-group"></div>');
                // Add Update buttons (possible to update params when pĥase is PENDING in UWS 1.0 - but not yet implemented)
                $('#id_'+pname).parent().append('<span class="input-group-btn"><button id="button_'+pname+'" class="btn btn-default" type="button">Update</button></span>');
                // Change input type
                displayParamFormInputType(pname, p);
            } else {
                // param is a file, but only a text is shown
                $('#id_'+pname).attr('disabled','disabled');
                if (!(pname in job.parameters)) {
                    $('#id_'+pname).wrap('<div class="input-group"></div>');
                    $('#id_'+pname).parent().append('<span class="input-group-addon" style="line-height: 1.4;"><small>default used</small></span>');
                };
            };
            // Change right corners for checkbox and select inside input-group
            if (p.datatype.indexOf('bool') > -1) {
                $('#id_'+pname).parent().attr('style','border-bottom-right-radius: 0px; border-top-right-radius: 0px;');
            };
            if (p.options) {
                $('button[data-id=id_'+pname+']').attr('style','border-bottom-right-radius: 0px; border-top-right-radius: 0px; opacity: 1;');
            };
        };
        // Add control parameters if they are set
        for (var pkey in jdl.control_parameters_keys) {
            var pname = jdl.control_parameters_keys[pkey];
            if (pname in job.parameters) {
                if ($('#id_' + pname).length == 0) {
                    var pdesc = jdl.control_parameters[pname];
                    displayParamFormInput(pname, {'default': '', 'annotation': pdesc})
                };
                $('#id_'+pname).attr('disabled','disabled');
            };
        };
        // Disable Update button if job is not PENDING
        if (job.phase != 'PENDING') {
            //$('#id_'+pname).removeAttr('readonly');
            //$('#id_'+pname).removeAttr('disabled');
            //$('#button_'+pname).removeAttr('disabled');
            $('#job_params input').attr('disabled','disabled');
            $('#job_params select').attr('disabled','disabled');
            $('#job_params button').attr('disabled','disabled');
        };
        // Fill value from job
        $('#job_params').append('<input id="all_params" name="all_params" type="hidden" value=""/>');
        var qs = {};
        for (var pname in job.parameters) {
            var pvalue = job.parameters[pname].value;
            pvalue = decodeURIComponent(pvalue).replace(/[+]/g, " ");
            if (pname != 'control_parameters') {
                qs[pname] = pvalue;
            };
            // Add in param_list table (if present in DOM)
            $('#param_list').append('<tr><td><strong>' + pname + '</strong></td><td>' + pvalue + '</td></tr>');
            // Update form fields
            $('#id_' + pname).attr('value', pvalue);
        };
        $('.selectpicker').selectpicker('refresh');
        $('#all_params').attr('value', JSON.stringify(qs));
        // Add buttons
        var elt = '\
            <div id="form-buttons" class="form-group">\n\
                <div class="col-md-offset-2 col-md-5">\n\
                    <button id="showopt" type="button" class="btn btn-default">Show optional parameters</button>\n\
                </div>\n\
            </div>\n';
        $('#job_params').append(elt);
        $('#showopt').click( function() {
            var btext = $('#showopt').html();
            if (btext.indexOf('Show') > -1) {
                $('.optional').show();
                $('#showopt').html("Hide optional parameters");
            } else {
                $('.optional').hide();
                $('#showopt').html("Show optional parameters");
            };
        });

    };
    var displayParamForm = function(jobName, init_params){
        $('#loading').show();
        wait_for_jdl(jobName, displayParamFormOk, [jobName, init_params]);
    };
    var displayParams = function(job){
        $('#loading').show();
        wait_for_jdl(job.jobName, displayParamFormOkFilled, [job]);
    };


    //----------
    // DISPLAY RESULTS

    var displayResult = function(list, r, r_fname, r_type, r_url, r_url_auth){
        var rsplit = r.replace(/\./g, '_')
        var r_id = 'result_'+rsplit
        var r_url_base = r_url.split('?ID=')[0];
        var r_name = r_url.split('/').pop();
        var r_eid = r_name.split('?ID=').pop();
        var r_fname_display = "";
        if (r_fname && r_fname.length != 0) {
            r_fname_display = ": " + r_fname;
        }
        var r_panel = '\
            <div id="'+r_id+'" class="panel panel-default" value="'+r_url+'">\
                <div class="panel-heading clearfix">\
                    <span class="pull-left" style="padding-top: 4px;">\
                        <span class="panel-title"><strong>'+r+'</strong>'+r_fname_display+'</span> ['+r_type+']\
                    </span>\
                    <div class="btn-group pull-right">\
                    </div>\
                </div>\
            </div>';
        // Add to list
        $('#'+list).append(r_panel);
        // Some results are shown in the details box if present
        // $('#'+r_id+' div.panel-heading span a').html('Download ['+r_type+']');
        // Add download button through proxy (with auth)
        $('#'+r_id+' div.panel-heading div.btn-group').append('\
            <a class="preview btn btn-default btn-sm">\
                <span class="glyphicon glyphicon-eye-open"></span>\
                Show preview\
            </a>\
            <a class="download btn btn-default btn-sm" href="' + r_url_auth + '">\
                <span class="glyphicon glyphicon-save"></span>\
                Download\
            </a>'
        );
//            <a class="adownload btn btn-default btn-sm" href="' + r_url + '">\
//                <span class="glyphicon glyphicon-save"></span>\
//                Anonymous Download\
//            </a>'
        // Show preview according to result type (file extension)
        switch (r_type) {
            // FITS files can be SAMPed
            case 'image/fits':
                // Show image preview
                $('#'+r_id+' div.panel-heading div.btn-group a.preview').hide();
                //$('#'+r_id+' div.panel-body').html('\
                //    <img class="img-thumbnail" src="/static/images/crab_cta.png" />\
                //');
                // Add SAMP button
                $('#'+r_id+' div.panel-heading div.btn-group').append('\
                    <button type="button" class="samp btn btn-default btn-sm"><span class="glyphicon glyphicon-send"></span> SAMP</button>'
                );
                // Add event on SAMP button click
                $('#'+r_id+' div.panel-heading div.btn-group button.samp').click(function() {
                    // var url = $(this).parents(".panel").attr('value');
                    //var name = url.split('/').pop();
                    var url_result = r_url_base + "/" + r_eid + "/" + r + ".fits";
                    console.log(url_result);
                    samp_client.samp_fits(url_result, r + ".fits");
                });
                break;
            // Show images
            case 'image/jpeg':
            case 'image/png':
            case 'image/gif':
                // Show image preview
                $('#'+r_id+' div.panel-heading div.btn-group a.preview').click(function() {
                    var txt = $(this).html();
                    if (!($('#'+r_id).hasClass('preview_loaded'))) {
                        $('#'+r_id).append('\
                            <div class="panel-body">\
                                <img class="img-thumbnail" src="' + r_url_auth + '" />\
                            </div>\
                        ');
                        $('#'+r_id).addClass('preview_loaded');
                        console.log('Preview loaded for ' + r_id);
                    };
                    if (txt.indexOf('Show') !== -1) {
                        $('#'+r_id+' div.panel-body').show();
                        $(this).html(txt.replace('Show', 'Hide').replace('open', 'close'));
                    } else {
                        $('#'+r_id+' div.panel-body').hide();
                        $(this).html(txt.replace('Hide', 'Show').replace('close', 'open'));
                    };
                });
                break;
            // Show text in textarea
            case 'text/plain':
            case 'text/xml':
            case 'application/json':
                // show textarea with log
                $('#'+r_id+' div.panel-heading div.btn-group a.preview').click(function() {
                    var txt = $(this).html();
                    if (!($('#'+r_id).hasClass('preview_loaded'))) {
                        $('#'+r_id).append('\
                            <div class="panel-body">\
                                <textarea class="log form-control" rows="10" style="font-family: monospace;" readonly>\
                                </textarea>\
                            </div>\
                        ');
                        $('#loading').show();
                        $.ajax({
                            url : r_url_auth,
                            dataType: "text",
                            context: r_id,  // Set this=r_id for success function
                            success: function (txt) {
                                $('#loading').hide();
                                if (r_type == 'application/json') {
                                    $('#' + this + ' div.panel-body textarea').html(JSON.stringify(JSON.parse(txt),
                                    undefined, 2));
                                } else {
                                    $('#' + this + ' div.panel-body textarea').html(txt);
                                }
                                $('#'+r_id).addClass('preview_loaded');
                                console.log('Preview loaded for ' + this);
                            },
                            error: function(xhr, status, exception) {
                                $('#loading').hide();
                                console.log(exception);
                            }
                        });
                    };
                    if (txt.indexOf('Show') !== -1) {
                        $('#'+r_id+' div.panel-body').show();
                        $(this).html(txt.replace('Show', 'Hide').replace('open', 'close'));
                    } else {
                        $('#'+r_id+' div.panel-body').hide();
                        $(this).html(txt.replace('Hide', 'Show').replace('close', 'open'));
                    };
                });
                break;
            // Show SVG
            case 'image/svg+xml':
                $('#'+r_id+' div.panel-heading div.btn-group a.preview').click(function() {
                    var txt = $(this).html();
                    if (!($('#'+r_id).hasClass('preview_loaded'))) {
                        $('#'+r_id).append('\
                            <div class="panel-body">\
                            </div>\
                        ');
                        var r_id_svg = r_id
                        $('#'+r_id+' div.panel-body').load(r_url_auth, function() {
                            $('#' + r_id_svg + ' > div.panel-body > svg').attr('width', '100%');
                        });
                        $('#'+r_id).addClass('preview_loaded');
                        console.log('Preview loaded for ' + r_id);
                    };
                    if (txt.indexOf('Show') !== -1) {
                        $('#'+r_id+' div.panel-body').show();
                        $(this).html(txt.replace('Show', 'Hide').replace('open', 'close'));
                    } else {
                        $('#'+r_id+' div.panel-body').hide();
                        $(this).html(txt.replace('Hide', 'Show').replace('close', 'open'));
                    };
                });
                break;
            // Unknown content_type
            default:
                $('#'+r_id+' div.panel-heading div.btn-group a.preview').hide();
        };
    };
    var displayResultsOk = function(job){
        $('#loading').hide();
        var jdl = clients[job.jobName].jdl;
        var serviceUrl = clients[job.jobName].serviceUrl;
        var details_keys =['jdl', 'stdout','stderr','provjson','provxml','provsvg'];
        var final_phase = ['COMPLETED', 'ABORTED', 'ERROR']
        $('#results_list').html('');
        //var generated_keys = jdl.generated_keys.concat(['stdout','stderr','provjson','provxml','provsvg']);
        for (var rkey in jdl.generated_keys) {
            var r = jdl.generated_keys[rkey];
            // if r is in job.results
            if ($.inArray(r, Object.keys(job.results)) !== -1) {
                var r_url = job.results[r].href;
                var r_type = job.results[r].mimetype;
                var r_fname = job.results[r].filename;
                var r_url_auth = r_url.split('?').pop();
                if (r_url_auth != r_url) {
                    r_url_auth = client_endpoint + client_endpoint_proxy + server_endpoint_results + '?' + r_url_auth
                };
                // var r_type = jdl.generated[r]['content_type']; //r_name.split('.').pop();
                displayResult('results_list', r, r_fname, r_type, r_url, r_url_auth);
            };
        };
        for (var r in job.results) {
            if (jdl.generated_keys.includes(r) == false) {
                if (details_keys.includes(r) == false) {
                    logger('INFO', 'additional result found: ' + r);
                    var r_url = job.results[r].href;
                    var r_type = job.results[r].mimetype;
                    var r_fname = job.results[r].name;
                    var r_url_auth = r_url.split('?').pop();
                    if (r_url_auth != r_url) {
                        r_url_auth = client_endpoint + client_endpoint_proxy + server_endpoint_results + '?' + r_url_auth
                    };
                    displayResult('results_list', r, r_fname, r_type, r_url, r_url_auth);
                };
            };
        };
        $('#details_list').html('');
        for (var rkey in details_keys) {
            var r = details_keys[rkey];
            if ($.inArray(r, Object.keys(job.results)) !== -1) {
                var r_url = serviceUrl + '/' + job.jobId + '/' + r;
                var r_url_auth = client_endpoint + client_endpoint_proxy + server_endpoint_jobs + '/' + job.jobName + '/' + job.jobId + '/' + r;
                var r_type = 'text/plain';
                switch (r) {
                    case 'provjson':
                        r_type = 'application/json'
                        break;
                    case 'provxml':
                        r_type = 'text/xml'
                        break;
                    case 'provsvg':
                        r_type = 'image/svg+xml'
                        break;
                };
                if (final_phase.includes(job.phase)) {
                    displayResult('details_list', r, r, r_type, r_url, r_url_auth);
                };
            };
        };
    };
    var displayResults = function(job){
        $('#loading').show();
        wait_for_jdl(job.jobName, displayResultsOk, [job]);
    };


    //----------
    // DISPLAY SINGLE JOB INFO

    var displaySingleJobOk = function(jobName, jobId){
        $('#loading').show();
        prepareTable();
        clients[jobName].getJobInfos(jobId, displaySingleJobSuccess, displaySingleJobError);
    };
    var displaySingleJob = function(jobName, jobId){
        $('#loading').show();
        wait_for_jdl(jobName, displaySingleJobOk, [jobName, jobId]);
    };
    var displaySingleJobSuccess = function(job){
        $('#loading').hide();
        displayJobRow(job);
        // Display properties in table prop_list
        displayProps(job);
        // Display parameters in id_* fields
        displayParamFormOkFilled(job);
        // Display results as panels in div results
        displayResultsOk(job);
        // Show div_job
        $("#div_job").show();
        // Slide to
        var hash = window.location.hash.substring(1);
        if (hash != 'results') {
            if ($("#"+hash+"_btn").hasClass("collapsed")) {
                $("#"+hash+"_panel").collapse("show");
                $("#"+hash+"_btn").removeClass("collapsed");
            };
        };
        if (hash != 'properties') {
            scrollToAnchor(hash);
        };
        // Back to job list on remove
        // $("#"+job.jobId).on("remove", function () {
        $("#"+job.jobId).on('destroyed', function() {
            $("#div_job").hide();
            setTimeout(function(){
                window.location.href = client_endpoint + client_endpoint_jobs + "/" + job.jobName;  // + "?msg=deleted&jobid=" + jobId;
            }, 3000);
        });
        // Change click event for Details buttons
        $('#'+job.jobId+' td button.properties').click( function() {
            if ($("#properties_btn").hasClass("collapsed")) {
                $("#properties_panel").collapse("show");
                $("#properties_btn").removeClass("collapsed");
            };
            scrollToAnchor('properties');
        });
        $('#'+job.jobId+' td button.parameters').click( function() {
            if ($("#parameters_btn").hasClass("collapsed")) {
                $("#parameters_panel").collapse("show");
                $("#parameters_btn").removeClass("collapsed");
            };
            scrollToAnchor('parameters');
        });
        $('#'+job.jobId+' td button.results').click( function() {
            if ($("#results_btn").hasClass("collapsed")) {
                $("#results_panel").collapse("show");
                $("#results_btn").removeClass("collapsed");
            };
            scrollToAnchor('results');
        });
    };
    var displaySingleJobError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        $("#div_job").hide();
        var msg = '<strong>Job does not exist</strong>: ' + jobId + ', going back to job list'
        global.showMessage(msg, 'warning');
        logger('WARNING', 'displaySingleJob '+ jobId, exception);
        setTimeout(function(){
            window.location.href = client_endpoint + client_endpoint_jobs;  // + "?msg=missing&jobid=" + jobId;
        }, 3000);
    };


    //----------
    // REFRESH PROPS

    var refreshProps = function(jobId){
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobInfos(jobId, refreshPropsSuccess, refreshPropsError);
    };
    var refreshPropsSuccess = function(job){
        $('#loading').hide();
        $("#prop_list").html('');
        displayProps(job);
        logger('DEBUG', 'Properties refreshed');
    };
    var refreshPropsError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'refreshProps '+ jobId, exception);
        var msg = 'Cannot refresh properties of job ' + jobId;
        global.showMessage(msg, 'danger');
    };


    //----------
    // REFRESH RESULTS

    var refreshResults = function(jobId){
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobInfos(jobId, refreshResultsSuccess, refreshResultsError);
    };
    var refreshResultsSuccess = function(job){
        $('#loading').hide();
        displayResults(job);
        logger('DEBUG', 'Results refreshed');
    };
    var refreshResultsError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'refreshResults '+ jobId, exception);
        var msg = 'Cannot refresh results of job ' + jobId;
        global.showMessage(msg, 'danger');
    };



    //----------
    // GET functions
    //----------


    //----------
    // GET JOB LIST

    var getJobList = function() {
        prepareTable();
        for (var i in jobNames) {
            $('#loading').show();
            var jobName = jobNames[i];
            logger('INFO', 'Get job list for ' + jobName);
            clients[jobName].getJobList(getJobListSuccess, getJobListError);
            // clients[jobName].getJobListInfos(getJobListSuccess, getJobListError);
        };
    };
    var getJobListSuccess = function(jobs) {
        $('#loading').hide();
        if (jobs.length == 0){
            //$('#job_list').html(' ');
            logger('INFO', 'Job list is empty');
        } else {
            logger('INFO', 'Displaying job list, containing ' + jobs.length + ' jobs...');
            for (var i = 0; i < jobs.length; i++) {
                var job = jobs[i];
                if (!$('#'+job.jobId).length) {
                    displayJob(job);
                };
            };
        };
        // Use tablesorter
        //var col_sort = job_list_columns.indexOf('creationTime');
        var col_sort = $("th").index($("#creationTime"));
        console.log(col_sort);
        $("#job_list").tablesorter({
            theme : "bootstrap",
            headerTemplate : '{content} {icon}',
            sortReset: true,
            sortRestart : true,
            widgets : [ "uitheme", "zebra" ],
        })
        .tablesorterPager({
            // target the pager markup - see the HTML block below
            container: $(".ts-pager"),
            // target the pager page select dropdown - choose a page
            cssGoto  : ".pagenum",
            // remove rows from the table to speed up the sort of large tables.
            // setting this to false, only hides the non-visible rows; needed if you plan to add/remove rows with the pager enabled.
            removeRows: false,
            // output string - default is '{page}/{totalPages}';
            // possible variables: {page}, {totalPages}, {filteredPages}, {startRow}, {endRow}, {filteredRows} and {totalRows}
            output: '{startRow} - {endRow} / {filteredRows} ({totalRows})'
        });

        $("#job_list").trigger("updateAll", true);
        logger('INFO', 'Job list loaded ');
        $('#div_table').show();
    };
    var getJobListError = function(xhr, status, exception) {
        $('#loading').hide();
        //var responseJSON = $.parseJSON( xhr.responseText );
        //var dataHtml = $($.parseHTML(xhr.responseText)).children('html');
        //$('pre', $(dataHtml)).each( function() {
        //    // 'this' refers to the pre element
        //    $(this).html();
        //});
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        logger('ERROR', 'getJobList', msg);
        global.showMessage(msg, 'danger');
    };


    //----------
    // GET JOB PHASE

    var getJobPhase = function(jobId) {
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobPhase(jobId, getJobPhaseSuccess, getJobPhaseError);
    };
    var getJobPhaseSuccess = function(jobId, phase) {
        var phase_init = $('#'+jobId+' td button.phase').html().split(";").pop();
        clearTimeout(refreshPhaseTimeout[jobId]);
        logger('INFO', 'Phase is '+phase+' (was '+phase_init+') for job '+jobId);
        //logger('DEBUG',phase_init+' --> '+phase);
        if (phase != phase_init) {
            refreshPhaseTimeoutDelay[jobId] = timeoutDelays[0]
            refreshPhase(jobId, phase);
        }
        else{
            // Refresh phase if change is expected
            switch (phase) {
                case 'QUEUED':
                case 'EXECUTING':
                case 'UNKNOWN':
                case 'SUSPENDED':
                    var timeoutDelaysId = timeoutDelays.indexOf(refreshPhaseTimeoutDelay[jobId])
                    if (timeoutDelaysId < timeoutDelays.length - 1) {
                        refreshPhaseTimeoutDelay[jobId] = timeoutDelays[timeoutDelaysId + 1]
                    }
                    refreshPhaseTimeout[jobId] = setTimeout(getJobPhase, refreshPhaseTimeoutDelay[jobId], jobId);
            }
        };
        //add timeout if phase is QUEUED, EXECUTING,
        //refreshPhaseTimeout[jobId] = setTimeout(getJobPhase, refreshPhaseTimeoutDelay[jobId], jobId);

    };
    var getJobPhaseError = function(jobId, xhr, status, exception){
        logger('ERROR', 'getJobPhase '+ jobId, exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot get phase of job ' + jobId + ': ' + msg;
        global.showMessage(msg, 'danger');
    };


    //----------
    // GET JOB INFO

    var getJobInfos = function(jobId){
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobInfos(jobId,getJobInfosSuccess, getJobInfosError);
    };
    var getJobInfosSuccess = function(job){
        $('#loading').hide();
        alert(JSON.stringify(job, null, 4));
    };
    var getJobInfosError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'getJobInfos '+ jobId, exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot get info of job ' + jobId + ': ' + msg;
        global.showMessage(msg, 'danger');
    };


    //----------

    // GET JOB RESULTS
    var getJobResults = function(jobId){
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobResults(jobId, getJobResultsSuccess, getJobResultsError);
    };
    var getJobResultsSuccess = function(jobId, results){
        $('#loading').hide();
        alert('Results for job '+ jobId + ' :\n' + JSON.stringify(results, null, 4));
    };
    var getJobResultsError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'getJobResults '+ jobId, exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot get job results for job' + jobId + ': ' + msg;
        global.showMessage(msg, 'danger');
    };



    //----------
    // POST functions
    //----------


    //----------
    // CREATE JOB

    var createJob = function(jobName, jobParams) {
        $('#loading').show();
        var csrf_token = $('#csrf_token').attr('value');
        clients[jobName].createJob(jobParams, createJobSuccess, createJobError, csrf_token);
    };
    var createJobSuccess = function(job) {
        $('#loading').hide();
        logger('INFO', 'Job created with id='+job.jobId+' jobname='+job.jobName);
        // redirect to URL + job_id
        window.location.href = client_endpoint + client_endpoint_job_edit + "/" + job.jobName + "/" + job.jobId;
    };
    var createJobError = function(xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'createJob', exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot create job: ' + msg;
        global.showMessage(msg, 'danger');
    };


    //----------
    // CREATE TEST JOB

    var createTestJob = function(jobName, jobParams) {
        var csrf_token = $('#csrf_token').attr('value');
        clients[jobName].createJob(jobParams, createTestJobSuccess, createJobError, csrf_token);
    };
    var createTestJobSuccess = function(job) {
        $('#loading').hide();
        logger('INFO', 'Test job created with id='+job.jobId+' jobname='+job.jobName);
        displayJob(job);
    };


    //----------
    // START JOB

    var startJob = function(jobId, csrf_token='') {
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        var csrf_token = $('#csrf_token').attr('value');
        clients[jobName].startJob(jobId, startJobSuccess, startJobError, csrf_token);
    };
    var startJobSuccess = function(jobId) {
        $('#loading').hide();
        logger('INFO', 'Job started '+jobId);
        getJobPhase(jobId);
    };
    var startJobError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'startJob '+jobId, exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot start job ' + jobId + ': ' + msg;
        global.showMessage(msg, 'danger');
    };


    //----------
    // ABORT JOB

    var abortJob = function (jobId){
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        var csrf_token = $('#csrf_token').attr('value');
        clients[jobName].abortJob(jobId, abortJobSuccess, abortJobError, csrf_token);
    };
    var abortJobSuccess = function(jobId){
        $('#loading').hide();
        clearTimeout(refreshPhaseTimeout[jobId]);
        logger('INFO', 'Job aborted '+jobId);
        getJobPhase(jobId);
    };
    var abortJobError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'abortJob '+ jobId, exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot abort job ' + jobId + ': ' + msg;
        global.showMessage(msg, 'danger');
    };


    //----------
    // DESTROY JOB

    var destroyJob = function (jobId){
        $('#loading').show();
        var jobName = $('#'+jobId).attr('jobname');
        var csrf_token = $('#csrf_token').attr('value');
        clients[jobName].destroyJob(jobId, destroyJobSuccess, destroyJobError, csrf_token);
    };
    var destroyJobSuccess = function(jobId, jobs){
        $('#loading').hide();
        try {
            var msg = '<strong>Job deleted</strong>: '+jobId+', going back to job list';
            global.showMessage(msg, 'info');
            clearTimeout(refreshPhaseTimeout[jobId]);
            logger('INFO', 'Job deleted '+jobId);
            $('#'+jobId).remove();
        } catch (e) {
            logger('ERROR', 'destroyJobSuccess failed '+jobId, e);
        }
    };
    var destroyJobError = function(jobId, xhr, status, exception){
        $('#loading').hide();
        logger('ERROR', 'destroyJob '+jobId, exception);
        var msg = xhr.responseText.match(/<pre>[\s\S]*<\/pre>/g)
        if (msg && msg.length != 0) {
            msg = msg[0].replace(/<\/?pre>/g,'');
        }
        var msg = 'Cannot delete job ' + jobId + ': ' + msg;
        global.showMessage(msg, 'danger');
    };

    //----------

    return {
        initClient: initClient,
        prepareTable: prepareTable,
        getJobList: getJobList,
        selectJob: selectJob,
        createJob: createJob,
        createTestJob: createTestJob,
        displaySingleJob: displaySingleJob,
        displayParamForm: displayParamForm,
        displayParamFormInput: displayParamFormInput,
        client_endpoint: client_endpoint,
        client_endpoint_jdl: client_endpoint_jdl,
        client_endpoint_jobs: client_endpoint_jobs,
        client_endpoint_job_edit: client_endpoint_job_edit,
        client_endpoint_job_form: client_endpoint_job_form,
        client_endpoint_proxy: client_endpoint_proxy,
    }

})(jQuery);
