/*!
 * UWS Library
 * Copyright (c) 2015 by Cyril Chauvin
 * Licensed under MIT
 */
var uwsLib = (function() {
	"use strict";

	var readParameters = function(xml){
		var parameters = new Object();
		var parametersElement = $(xml).find("uws\\:parameters, parameters");
		$(parametersElement).find("uws\\:parameter, parameter").each(function(){
			var elementName = $(this).attr('id');
			parameters[elementName] = new Object();
			parameters[elementName].value = $(this).text();
			parameters[elementName].byref = $(this).attr('byref');
		});
		return parameters;
	};

	var readResults = function(xml){
		var results = new Object();
		var resultsElement = $(xml).find("uws\\:results, results");
		$(resultsElement).find("uws\\:result, result").each(function(){
			var elementName = $(this).attr('id');
			results[elementName] = new Object() ;
			results[elementName].href = $(this).attr("xlink:href");
			results[elementName].mimetype = $(this).attr("mime-type");
			results[elementName].filename = $(this).attr("name");
			results[elementName].hash = $(this).attr("hash");
		});
		return results;
	};
	
	var getJobFromXml = function (xml, jobName){
		var jobXmlElement = $(xml).find("uws\\:job, job");
		var job = new Object();
		job.jobName = jobName;
		job.jobId = $(jobXmlElement).find("uws\\:jobId, jobId").text();
		job.phase = $(jobXmlElement).find("uws\\:phase, phase").text();
		job.runId = $(jobXmlElement).find("uws\\:runId, runId").text();
		job.ownerId = $(jobXmlElement).find("uws\\:ownerId, ownerId").text();
		job.creationTime = $(jobXmlElement).find("uws\\:creationTime, creationTime").text();
		job.startTime = $(jobXmlElement).find("uws\\:startTime, startTime").text();
		job.endTime = $(jobXmlElement).find("uws\\:endTime, endTime").text();
		job.destruction = $(jobXmlElement).find("uws\\:destruction, destruction").text();
		job.executionDuration = $(jobXmlElement).find("uws\\:executionDuration, executionDuration").text();
		job.quote = $(jobXmlElement).find("uws\\:quote, quote").text();
		job.errorSummary = $(jobXmlElement).find("uws\\:errorSummary, errorSummary").text();
		job.parameters = readParameters(xml);
		job.results = readResults(xml);
		return job;
	};
	
	var getJobListFromXml = function (xml, jobName){
		var jobs = [];
		$(xml).find("uws\\:jobref, jobref").each(function(){
			var job = new Object();
			job.jobName = jobName;
			job.jobId = $(this).attr('id');
			job.phase = $(this).find('uws\\:phase, phase').text();
			job.runId = $(this).find("uws\\:runId, runId").text();
			job.ownerId = $(this).find("uws\\:ownerId, ownerId").text();
			job.creationTime = $(this).find("uws\\:creationTime, creationTime").text();
			jobs.push(job);
		});
		return jobs;
	};

	function uwsClient(serviceUrl){
		this.serviceUrl = serviceUrl;
		this.jobName = serviceUrl.split('/').pop();
	};
	
	//uwsClient.prototype.getJobListInfos
	
	uwsClient.prototype.getJobs = function(SuccessCallback, ErrorCallback){
		var jobName = this.jobName;
		$.ajax({
			url : this.serviceUrl,
			async : true,
			type : 'GET',
			dataType: "xml",
			success : function(xml) {
				var jobs = getJobListFromXml(xml, jobName);
				SuccessCallback(jobs);
			},
			error : function(xhr, status, exception) {
				ErrorCallback(xhr, status, exception);
			}
		});
	};

	uwsClient.prototype.createJob = function (jobParameters, SuccessCallback, ErrorCallback, csrf_token=''){
		var jobName = this.jobName;
		$.ajax({
			url : this.serviceUrl,
			async : true,
			type : 'POST',
			headers: { "X-CSRFToken": csrf_token },
			data : jobParameters,
			success : function(xml) {
				var job = getJobFromXml(xml, jobName);
				SuccessCallback(job);
			},
			error : function(xhr, status, exception) {
				ErrorCallback(xhr, status, exception);
			},
			processData: false,  // tell jQuery not to process the data
			contentType: false   // tell jQuery not to set contentType
		});
	};

	uwsClient.prototype.destroyJob = function(id, successCallback, errorCallback, csrf_token='') {
		var jobName = this.jobName;
		var post_data = {
			'ACTION': 'DELETE',
		}
		$.ajax({
			url : this.serviceUrl + "/" + id,
			type: 'POST',
			headers: { "X-CSRFToken": csrf_token },
			dataType: "xml",
			data: post_data,
			success : function(xml) {
				var jobs = getJobListFromXml(xml, jobName);
				successCallback(id, jobs);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, xhr, status, exception);
			},
		});
		
	};

	uwsClient.prototype.abortJob = function(id, successCallback, errorCallback, csrf_token='') {
		var post_data = {
			'PHASE': 'ABORT',
		}
		$.ajax({
			url : this.serviceUrl + "/" + id + "/phase",
			type: 'POST',
			headers: { "X-CSRFToken": csrf_token },
			dataType: "xml",
			data: post_data,
			success : function(xml) {
				successCallback(id);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, xhr, status, exception);
			},
		});
		
	};

	uwsClient.prototype.startJob = function(id, successCallback, errorCallback, csrf_token='') {
		var post_data = {
			'PHASE': 'RUN',
		}
		$.ajax({
			url : this.serviceUrl + "/" + id + "/phase",
			type: 'POST',
			headers: { "X-CSRFToken": csrf_token },
			dataType: "xml",
			data: post_data,
			success : function(xml) {
				successCallback(id);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, xhr, status, exception);
			},
		});
		
	};
	
	uwsClient.prototype.getJobInfos = function(id, successCallback, errorCallback) {
		var jobName = this.jobName;
		$.ajax({
			url : this.serviceUrl + "/" + id,
			type: 'GET',
			dataType: "xml",
			success : function(xml) {
				var job = getJobFromXml(xml, jobName);
				successCallback(job);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, xhr, status, exception);
			},
		});
	};
	uwsClient.prototype.getJobResults = function(id, successCallback, errorCallback) {
		$.ajax({
			url : this.serviceUrl + "/" + id + "/results",
			type: 'GET',
			dataType: "xml",
			success : function(xml) {
				var results = readResults(xml);
				successCallback(id, results);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, xhr, status, exception);
			},
		});
	};
	
	uwsClient.prototype.getJobPhase = function(id, successCallback, errorCallback) {
		$.ajax({
			url : this.serviceUrl + "/" + id + "/phase",
			type: 'GET',
			success : function(xhr) {
				successCallback(id, xhr);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, xhr, status, exception);
			},
		});
	};

	uwsClient.prototype.getJobList = function(successCallback, errorCallback) {
		var jobName = this.jobName;
		$.ajax({
			url : this.serviceUrl,
			type : 'GET',
			dataType: "xml",
			success : function(xml) {
				var jobList = getJobListFromXml(xml, jobName);
				successCallback(jobList);
			},
			error : function(xhr, status, exception) {
				errorCallback(xhr, status, exception);
			},
		});
	}

	uwsClient.prototype.getJobInfosSync = function(id) {
		return $.ajax({
			url : this.serviceUrl + "/" + id,
			async : false,
			type: 'GET',
			dataType: "xml",
		}).responseXML;
	}

	uwsClient.prototype.getJobListSync = function() {
		return $.ajax({
			url : this.serviceUrl,
			async : false,
			type : 'GET',
			dataType: "xml",
		}).responseXML;
	}

	uwsClient.prototype.getJobListInfosSync = function(successCallback, errorCallback) {
		var jobList = []
		var jobSummaryList = getJobListFromXml(this.getJobListSync(), this.jobName);
		console.log(jobSummaryList);
		for (var i in jobSummaryList){
			var id = jobSummaryList[i].jobId;
			var job = getJobFromXml(this.getJobInfosSync(id), this.jobName);
			jobList.push(job);
//			jobList.push(getJobFromXml(this.getJobInfosSync(jobSummaryList[i].jobId)));
		}
		console.log(jobList);
		successCallback(jobList);
	}

	uwsClient.prototype.getJobListInfos = function(successCallback, errorCallback) {
		var jobName = this.jobName;
		var serviceUrl = this.serviceUrl;
		$.ajax({
			url : serviceUrl,
			type : 'GET',
			dataType: "xml",
			success : function(xml) {
				var jobList = getJobListFromXml(xml, jobName);
                if ((jobList.length == 0)) {
                    successCallback(jobList);
                } else {
    				addJobListInfos(serviceUrl, jobName, jobList, successCallback, errorCallback);
    			};
			},
			error : function(xhr, status, exception) {
				errorCallback(xhr, status, exception);
			},
		});
	}

	function addJobListInfos(serviceUrl, jobName, jobSummaryList, successCallback, errorCallback) {
        var jobList = [];
        var currentIndex = 0;
        addJobInfos(serviceUrl, jobName, jobList, jobSummaryList, currentIndex, successCallback, errorCallback);
	}

    function addJobInfos(serviceUrl, jobName, jobList, jobSummaryList, currentIndex, successCallback, errorCallback) {
        var id = jobSummaryList[currentIndex].jobId;
        $.ajax({
            url: serviceUrl + "/" + id,
			type : 'GET',
			dataType: "xml",
            success: function(xml) {
                var job = getJobFromXml(xml, jobName);
                jobList.push(job);
            },
			error : function(xhr, status, exception) {
				errorCallback(xhr, status, exception);
			},
            complete: function() {
                currentIndex++;
                if (currentIndex == jobSummaryList.length) {
                    successCallback(jobList);
                }
                else
                {
                    addJobInfos(serviceUrl, jobName, jobList, jobSummaryList, currentIndex, successCallback, errorCallback);
                }
            }
        });
    }

	return {
		uwsClient: uwsClient,
//		getJobs : getJobs,
//		createJob : createJob,
//		destroyJob : destroyJob,
//		getJobInfos : getJobInfos,
//		getJobResults : getJobResults,
//		getJobPhase : getJobPhase
	}

})();



