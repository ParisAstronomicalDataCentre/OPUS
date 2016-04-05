/*!
 * UWS Manager
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

// The client fills a Job List table with id=job_list
// <table id="job_list" class="table table-bordered table-striped table-condensed"></table>

// It can also show the job parameters located in form inputs with id=id_*

// The properties are listed in a table with id=prop_list
// <table id='prop_list' class="table table-bordered table-striped table-condensed"></table>

// The results are shown as bootstrap panels in a div block with id=result_list
// <div id='result_list' class='text-center'></div>

var uws_manager = (function($) {
    "use strict";

    var refreshPhaseTimeout = {}; // stores setInterval functions for phase refresh
    var refreshPhaseTimeoutDelay = {}; //
    var timeoutDelays = [2000,3000,4000,5000,10000]; // delays in ms
    var selectedJobId;
    //var serviceUrl = "http://voparis-uws.obspm.fr/uws-v1.0/"; // app_url+"/uws-v1.0/" //
    var serviceUrl = $(location).attr('protocol') + '//' + $(location).attr('host');
    // "https://voparis-uws-test.obspm.fr/"; // app_url+"/uws-v1.0/" //
    var jobs_url = '/rest/';
    var jdl_url = '/get_jdl/';
    var form_upload_url = '/form_upload/';
    var job_list_url = '/client/job_list';
    var job_edit_url = '/client/job_edit';
    var jobNames;
    var clients = {};

    // LOGGER (show info in console, and send to Django)
    function logger(lvl_name, msg, exception) {
        console.log(lvl_name + ' ' + msg);
    }

    // Scroll to an anchor in the page with slow animation
    function scrollToAnchor(aid){
        var elt = $("#"+ aid);
        if (elt.length != 0) {
            $('html,body').animate( {scrollTop: elt.offset().top}, 'slow' );
        }
    }

    // CREATE MANAGER AND CLIENTS
    function initManager(jobNames_init){
        jobNames = jobNames_init;
        for (var i in jobNames) {
            // Init client
            clients[jobNames[i]] = new uwsLib.uwsClient(serviceUrl + jobs_url + jobNames[i]);
            // Get JDL for job
            $.getJSON(serviceUrl + jdl_url + jobNames[i], function(jdl) {
                clients[jobNames[i]].jdl = jdl;
            });
            logger('INFO', 'uwsClient at '+clients[jobNames[i]].serviceUrl);
        }
        logger('INFO', 'initManager '+serviceUrl);
    };

    function wait_for_jdl(jobName, next_function, args){
        if ((typeof clients[jobName] !== "undefined") && (typeof clients[jobName].jdl !== "undefined")) {
            console.log('JDL set for ' + jobName);
            next_function.apply(this, args);
        } else {
            console.log('Wait for JDL for ' + jobName);
            setTimeout(function(){
                wait_for_jdl(jobName, next_function, args);
            }, 500);
        };
    }

    // PREPARE TABLE
    var prepareTable = function() {
        var tcontent = '\
            <thead>\
                <tr>\
                    <th class="text-center">Type</th>\
                    <th class="text-center">Start Time</th>\
                    <th class="text-center">Destruction Time</th>\
                    <th class="text-center">Phase</th>\
                    <th class="text-center">Details</th>\
                    <th class="text-center">Control</th>\
                </tr>\
            </thead>\
            <tbody>\
            </tbody>';
        $('#job_list').html(tcontent);
    };

    // SELECT JOB
    var selectJob = function(jobId) {
        $('#job_list tbody').find('tr.bg-info').removeClass('bg-info');
        $('#'+jobId).addClass("bg-info");
    }

    //----------
    // DISPLAY functions

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
                break;
            case 'ABORTED':
                phase_class = 'btn-danger';
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
        if (phase == 'COMPLETED') {
            // Display results as panels in div results
            if ($("#result_list").length) {
                refreshResults(jobId);
            };
            logger('INFO', 'Job completed '+jobId);
        };
    };

    // DISPLAY JOB ROW
    var displayJobRow = function(job){
        var start_time = job.startTime.split("T");
        if (start_time.length == 1) {
            start_time = "";
        } else {
            start_time = start_time[0]+' '+start_time[1].split('+')[0];
        };
        var destr_time = job.destruction.split("T");
        if (destr_time.length == 1) {
            destr_time = "";
        } else {
            destr_time = destr_time[0]+' '+destr_time[1].split('+')[0];
        };
        var row = '\
            <tr id='+ job.jobId +' jobname='+ job.jobName +'>\
                <td class="text-center" style="vertical-align: middle;">' + job.jobName + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + start_time + '</td>\
                <td class="text-center" style="vertical-align: middle;">' + destr_time + '</td>\
                <td class="text-center" style="vertical-align: middle;">\
                    <button type="button" class="phase btn btn-default">PHASE...</button>\
                </td>\
                <td class="text-center">\
                    <div class="btn-group">\
                    <button type="button" class="properties btn btn-default">\
                        <span class="glyphicon glyphicon-info-sign"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Properties</span>\
                    </button>\
                    <button type="button" class="parameters btn btn-default">\
                        <span class="glyphicon glyphicon-edit"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;&nbsp;Parameters</span>\
                    </button>\
                    <button type="button" class="results btn btn-default">\
                        <span class="glyphicon glyphicon-open"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Results</span>\
                    </button>\
                    </div>\
                </td>\
                <td class="text-center">\
                    <div class="btn-group">\
                    <button type="button" class="start btn btn-default">\
                        <span class="glyphicon glyphicon-play"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Start</span>\
                    </button>\
                    <button type="button" class="abort btn btn-default">\
                        <span class="glyphicon glyphicon-off"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Abort</span>\
                    </button>\
                    <button type="button" class="delete btn btn-default">\
                        <span class="glyphicon glyphicon-trash"></span>\
                        <span class="hidden-xs hidden-sm hidden-md">&nbsp;Delete</span>\
                    </button>\
                    </div>\
                </td>\
            </tr>';
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

    // DISPLAY JOB
    var displayJob = function(job){
        // Display row
        displayJobRow(job);
        // Events for Details buttons
        $('#'+job.jobId+' td button.properties').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            selectJob(jobId);
            window.location.href = job_edit_url + "/" + jobName + "/" + jobId + '#properties';
        });
        $('#'+job.jobId+' td button.parameters').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            selectJob(jobId);
            window.location.href = job_edit_url + "/" + jobName + "/" + jobId + '#parameters';
        });
         $('#'+job.jobId+' td button.results').click( function() {
            var jobId = $(this).parents("tr").attr('id');
            var jobName = $(this).parents("tr").attr('jobname');
            selectJob(jobId);
            window.location.href = job_edit_url + "/" + jobName + "/" + jobId + '#results';
        });
    };

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

    // DISPLAY PARAMS
    var displayParamFormInput = function(pname, p){
        var row = '\
            <div class="form-group">\
                <label class="col-md-2 control-label">' + pname + '</label>\
                <div id="div_' + pname + '" class="col-md-5 controls">\
                    <input class="form-control" id="id_' + pname + '" name="' + pname + '" type="text" value="' + p.default + '"/>\
                </div>\
                <div class="col-md-5 help-block">\
                    ' + p.description + '\
                </div>\
            </div>';
        $('#job_params').append(row);
    };
    var displayParamFormInputType = function(pname, p){
        if (p.type == 'file') {
            $('#id_'+pname).attr('type', 'file');
        };
        if ((p.type.indexOf('long') > -1)
            || (p.type.indexOf('int') > -1)
            || (p.type.indexOf('float') > -1)
            || (p.type.indexOf('double') > -1)) {
            $('#id_'+pname).attr('type', 'number');
        };
        if (p.type.indexOf('anyURI') > -1) {
            $('#id_'+pname).attr('type', 'url');
        };
        if (p.type.indexOf('bool') > -1) {
            // Change to checkbox
            $('#id_'+pname).removeClass('form-control');
            $('#id_'+pname).attr('type', 'checkbox');
            $('#id_'+pname).wrap('<div class="checkbox"></div>');
            $('#id_'+pname).attr('style', 'margin-left: 10px;');
            var val = p.default.toLowerCase();
            if ((val == 'true') || (val == 'yes')) {
                $('#id_'+pname).attr('checked', 'checked');
            };
        };
        if (p.choices) {
            // change input to select and run selectpicker
            console.log('change to select');
            var elt = '\
                <select class="selectpicker" id="id_' + pname + '" name="' + pname + '">\n\
                </select>\n';

            $('#id_'+pname).replaceWith(elt);
            var choices = p.choices.split('|');
            for (var i in choices) {
                $('#id_'+pname).append('<option>' + choices[i] + '</option>');
                $('select[name=' + pname + ']').attr('data-width', '100%').selectpicker();
                $('select[name=' + pname + ']').val(p.default);
            };
            $('.selectpicker').selectpicker('refresh');
        };
    };
    var displayParamFormOk = function(jobName){
        // Run displayParamForm insread to check that jdl is defined
        var jdl = clients[jobName].jdl;
        // Create form fields from WADL/JDL
        for (var pname in jdl.parameters) {
            var p = jdl.parameters[pname];
            if (p.required.toLowerCase() == 'true') {
                displayParamFormInput(pname, p)
                displayParamFormInputType(pname, p)
            };
        };
        // Add buttons
        var elt = '\
            <div id="form-buttons" class="form-group">\n\
                <div class="col-md-offset-2 col-md-5">\n\
                    <button type="submit" class="btn btn-primary">Submit</button>\n\
                    <button type="reset" class="btn btn-default">Reset</button>\n\
                </div>\n\
            </div>\n';
        $('#job_params').append(elt);
    };
    var displayParamFormFilled = function(job){
        var jdl = clients[job.jobName].jdl;
        // Create form fields from WADL/JDL
        for (var pname in jdl.parameters) {
            var p = jdl.parameters[pname];
            displayParamFormInput(pname, p);
            if (p.type != 'file') {
                $('#id_'+pname).wrap('<div class="input-group"></div>');
                // Signal default value
                if (!(pname in job['parameters'])) {
                    $('#id_'+pname).parent().append('<span class="input-group-addon" style="line-height: 1.4;"><small>default used</small></span>');
                };
                // Add Update buttons (possible to update params when pĥase is PENDING in UWS 1.0 - but not yet implemented)
                $('#id_'+pname).parent().append('<span class="input-group-btn"><button id="button_'+pname+'" class="btn btn-default" type="button">Update</button></span>');
                // Change input type
                displayParamFormInputType(pname, p);
            } else {
                $('#id_'+pname).attr('disabled','disabled');
                if (!(pname in job['parameters'])) {
                    $('#id_'+pname).wrap('<div class="input-group"></div>');
                    $('#id_'+pname).parent().append('<span class="input-group-addon" style="line-height: 1.4;"><small>default used</small></span>');
                };
            };
            // Change right corners for checkbox and select inside input-group
            if (p.type.indexOf('bool') > -1) {
                $('#id_'+pname).parent().attr('style','border-bottom-right-radius: 0px; border-top-right-radius: 0px;');
            };
            if (p.choices) {
                $('button[data-id=id_'+pname+']').attr('style','border-bottom-right-radius: 0px; border-top-right-radius: 0px; opacity: 1;');
            };
        };
        // Disable button if job is not PENDING
        if (job['phase'] != 'PENDING') {
            //$('#id_'+pname).removeAttr('readonly');
            //$('#id_'+pname).removeAttr('disabled');
            //$('#button_'+pname).removeAttr('disabled');
            $('#job_params input').attr('disabled','disabled');
            $('#job_params select').attr('disabled','disabled');
            $('#job_params button').attr('disabled','disabled');
        };
        // Fill value
        for (var pname in job['parameters']) {
            var pvalue = job['parameters'][pname];
            // Add in param_list table (if present in DOM)
            $('#param_list').append('<tr><td><strong>'+pname+'</strong></td><td>'+decodeURIComponent(pvalue)+'</td></tr>');
            // Update form fields
            $('#id_'+pname).attr('value', decodeURIComponent(pvalue));
        };
        $('.selectpicker').selectpicker('refresh');
    };
    var displayParamForm = function(jobName){
        wait_for_jdl(jobName, displayParamFormOk, [jobName]);
    };
    var displayParams = function(job){
        wait_for_jdl(job.jobName, displayParamFormFilled, [job]);
    };

    // DISPLAY RESULTS
    var displayResults = function(job){
        $('#result_list').html('');
        var r_i = 0;
        for (var r in job['results']) {
            r_i++;
            var r_id = 'result_'+r
            var r_url = job['results'][r];
            var r_name = r_url.split('/').pop();
            var r_type = r_name.split('.').pop();
            var r_panel = '\
                <div id="'+r_id+'" class="panel panel-default" value="'+r_url+'">\
                      <div class="panel-heading clearfix">\
                          <span class="pull-left">\
                              <span class="panel-title"><strong>'+r_id+'</strong></span>: \
                              <a href="'+r_url+'" target="_blank">'+r_url+'</a>\
                          </span>\
                      </div>\
                </div>';
            $('#result_list').append(r_panel);
            switch (r_type) {
                case 'fits':
                    $('#'+r_id+' div.panel-heading span.pull-left').attr('style', "padding-top: 4px;");
                    $('#'+r_id+' div.panel-heading').append('\
                        <button type="button" class="samp btn btn-default btn-sm pull-right">SAMP</button>\
                    ');
                    // Add event on SAMP button click
                    $('#'+r_id+' div.panel-heading button.samp').click(function() {
                        console.log('samp!');
                        var url = $(this).parents(".panel").attr('value');
                        var name = url.split('/').pop();
                        samp_client.samp_image(url, name);
                    });
                    // Show image preview
                    //$('#'+r_id+' div.panel-body').html('\
                    //    <img class="img-thumbnail" src="/static/images/crab_cta.png" />\
                    //');
                    break;
                case 'jpg':
                case 'png':
                    // Show image preview
                    $('#'+r_id).append('\
                        <div class="panel-body">\
                            <img class="img-thumbnail" src="' + r_url + '" />\
                        </div>\
                    ');
                    break;
                case 'txt':
                case 'log':
                    // show textarea with log
                    $('#'+r_id).append('\
                        <div class="panel-body">\
                            <textarea class="log form-control" rows="10" style="font-family: monospace;" readonly></textarea>\
                        </div>\
                    ');
                    $.ajax({
                        url : r_url,
                        dataType: "text",
                        async: false,  // makes request synchronous
                        success : function (txt) {
                            $('#'+r_id+' div.panel-body textarea').html(txt);
                        }
                    });
                    break;
                case 'svg':
                    $('#'+r_id).append('\
                        <div class="panel-body">\
                        </div>\
                    ');
                    $('#'+r_id+' div.panel-body').load(r_url, function() {
                        $('#'+r_id+' > div.panel-body > svg').attr('width', '100%');
                    });
                    break;
            };
        };
    };

    // DISPLAY SINGLE JOB INFO
    var displaySingleJob = function(jobName, jobId){
        prepareTable();
        clients[jobName].getJobInfos(jobId, displaySingleJobSuccess, displaySingleJobError);
    };
    var displaySingleJobSuccess = function(job){
        displayJobRow(job);
        // Display properties in table prop_list
        displayProps(job);
        // Display parameters in id_* fields
        displayParams(job);
        // Display results as panels in div results
        displayResults(job);
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
        $("#"+job.jobId).on("remove", function () {
            var jobId = $(this).attr('id');
            var jobName = $(this).attr('jobname');
            $("#div_job").hide();
            $("#div_info").html('<strong>Job deleted</strong>: '+jobId+', going back to job list').addClass('alert alert-success');
            setTimeout(function(){
                window.location.href = job_list_url + "?jobname=" + jobName + "&msg=deleted&jobid=" + jobId;
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
    var displaySingleJobError = function(jobId, exception){
        $("#div_job").hide();
        $("#div_info").html('<strong>Job does not exist</strong>: '+jobId+', going back to job list').addClass('alert alert-warning');
        logger('WARNING', 'displaySingleJob '+ jobId, exception);
        setTimeout(function(){
            window.location.href = job_list_url + "?msg=missing&jobid=" + jobId;
        }, 3000);
    };

    // REFRESH PROPS
    var refreshProps = function(jobId){
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobInfos(jobId, refreshPropsSuccess, refreshPropsError);
    };
    var refreshPropsSuccess = function(job){
        $("#prop_list").html('');
        displayProps(job);
        logger('DEBUG', 'Properties refreshed');
    };
    var refreshPropsError = function(jobId, exception){
        logger('ERROR', 'refreshProps '+ jobId, exception);
    };

    // REFRESH RESULTS
    var refreshResults = function(jobId){
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobInfos(jobId, refreshResultsSuccess, refreshResultsError);
    };
    var refreshResultsSuccess = function(job){
        displayResults(job);
        logger('DEBUG', 'Results refreshed');
    };
    var refreshResultsError = function(jobId, exception){
        logger('ERROR', 'refreshResults '+ jobId, exception);
    };


    //----------
    // GET functions

    // GET JOB LIST
    var getJobList = function() {
        $('#div_table').hide();
        $('#div_loading').show();
        prepareTable();
        for (var i in jobNames) {
            var jobName = jobNames[i];
            logger('INFO', 'Get job list for '+jobName);
            clients[jobName].getJobListInfos(getJobListSuccess,getJobListError);
        }
    };
    var getJobListSuccess = function(jobs) {
        if (jobs.length == 0){
            //$('#job_list').html(' ');
            logger('INFO', 'Job list is empty');
        }
        else{
            logger('INFO', 'Displaying job list...');
            for (var i = 0; i < jobs.length; i++) {
                var job = jobs[i];
                displayJob(job);
            }
            //$( "#job_list" ).tablesorter({sortList: [[1,1]]});
            logger('INFO', 'Job list loaded');
        }
        $('#div_loading').hide();
        $('#div_table').show();
    };
    var getJobListError = function(exception) {
        logger('ERROR', 'getJobList', exception);
    };

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
    var getJobPhaseError = function(jobId, exception){
        logger('ERROR', 'getJobPhase '+ jobId, exception);
    };

    // GET JOB INFO
    var getJobInfos = function(jobId){
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobInfos(jobId,getJobInfosSuccess, getJobInfosError);
    };
    var getJobInfosSuccess = function(job){
        alert(JSON.stringify(job, null, 4));
    };
    var getJobInfosError = function(jobId, exception){
        logger('ERROR', 'getJobInfos '+ jobId, exception);
    };

    // GET JOB RESULTS
    var getJobResults = function(jobId){
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].getJobResults(jobId, getJobResultsSuccess, getJobResultsError);
    };
    var getJobResultsSuccess = function(jobId, results){
        alert('Results for job '+ jobId + ' :\n' + JSON.stringify(results, null, 4));
    };
    var getJobResultsError = function(jobId, exception){
        logger('ERROR', 'getJobResults '+ jobId, exception);
    };

    //----------
    // POST functions

    // CREATE JOB
    var createJob = function(jobName, jobParams) {
        clients[jobName].createJob(jobParams, createJobSuccess, createJobError);
    };
    var createJobSuccess = function(job) {
        logger('INFO', 'Job created with id='+job.jobId+' jobname='+job.jobName);
        // redirect to URL + job_id
        window.location.href = job_edit_url + "/" + job.jobName + "/" + job.jobId;
    };
    var createJobError = function(exception){
        logger('ERROR', 'createJob', exception);
    };

    // CREATE TEST JOB
    var createTestJob = function(jobName, jobParams) {
        clients[jobName].createJob(jobParams, createTestJobSuccess, createTestJobError);
    };
    var createTestJobSuccess = function(job) {
        logger('INFO', 'Test job created with id='+job.jobId+' jobname='+job.jobName);
        displayJob(job);
    };
    var createTestJobError = function(exception){
        logger('ERROR', 'createTestJob', exception);
    };

    // START JOB
    var startJob = function(jobId) {
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].startJob(jobId, startJobSuccess, startJobError);
    };
    var startJobSuccess = function(jobId) {
        logger('INFO', 'Job started '+jobId);
        getJobPhase(jobId);
    };
    var startJobError = function(jobId, exception){
        logger('ERROR', 'startJob '+jobId, exception);
    };

    // ABORT JOB
    var abortJob = function (jobId){
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].abortJob(jobId, abortJobSuccess, abortJobError);
    };
    var abortJobSuccess = function(jobId){
        clearTimeout(refreshPhaseTimeout[jobId]);
        logger('INFO', 'Job aborted '+jobId);
        getJobPhase(jobId);
    };
    var abortJobError = function(jobId, exception){
        logger('ERROR', 'abortJob '+ jobId, exception);
    };

    // DESTROY JOB
    var destroyJob = function (jobId){
        var jobName = $('#'+jobId).attr('jobname');
        clients[jobName].destroyJob(jobId, destroyJobSuccess, destroyJobError);
    };
    var destroyJobSuccess = function(jobId, jobs){
        try {
            clearTimeout(refreshPhaseTimeout[jobId]);
            logger('INFO', 'Job deleted '+jobId);
            $('#'+jobId).remove();
        } catch (e) {
            logger('ERROR', 'destroyJobSuccess failed '+jobId, e);
        }
    };
    var destroyJobError = function(jobId, exception){
        logger('ERROR', 'destroyJob '+jobId, exception);
    };

    //
    return {
        initManager: initManager,
        prepareTable: prepareTable,
        getJobList: getJobList,
        selectJob: selectJob,
        createJob: createJob,
        createTestJob: createTestJob,
        displaySingleJob: displaySingleJob,
        displayParamForm: displayParamForm
    }

})(jQuery);
