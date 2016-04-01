var uwsLib = (function() {
	"use strict";

	var readResults = function(xml){
		var results = new Object();
		var resultsElement = $(xml).find("uws\\:results, results");
		$(resultsElement).find("uws\\:result, result").each(function(){
			var elementName = $(this).attr('id');
			var elementValue = $(this).attr("xlink:href");
			results[elementName] = elementValue ;
		});
		return results;
	};
	
	var getJobFromXml = function (xml, jobName){
		var jobXmlElement = $(xml).find("uws\\:job, job");
		var job = new Object();
		job.jobName = jobName;
		job.jobId = $(jobXmlElement).find("uws\\:jobId, jobId").text();
		job.phase = $(jobXmlElement).find("uws\\:phase, phase").text();
		job.startTime = $(jobXmlElement).find("uws\\:startTime, startTime").text();
		job.endTime = $(jobXmlElement).find("uws\\:endTime, endTime").text();
		job.destruction = $(jobXmlElement).find("uws\\:destruction, destruction").text();
		job.executionDuration = $(jobXmlElement).find("uws\\:executionDuration, executionDuration").text();
		job.quote = $(jobXmlElement).find("uws\\:quote, quote").text();
		job.error = $(jobXmlElement).find("uws\\:error, error").text();
		job.ownerId = $(jobXmlElement).find("uws\\:ownerId, ownerId").text();
		job.runId = $(jobXmlElement).find("uws\\:runId, runId").text();
		job.parameters = new Object();
		var parametersElement = $(jobXmlElement).find("uws\\:parameters, parameters");
		$(parametersElement).find("uws\\:parameter, parameter").each(function(){
			var elementName = $(this).attr('id');
			var elementValue = $(this).text();
			job.parameters[elementName] = elementValue ;
		});
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
			jobs.push(job);
		});
		return jobs;
	};
	
	
	function uwsClient(serviceUrl){
		this.serviceUrl = serviceUrl;
		this.jobName = serviceUrl.split('/').pop();
	};
	
	uwsClient.prototype.getJobListInfos
	
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
				ErrorCallback(exception);
			}
		});
	};
	uwsClient.prototype.createJob = function (jobParameters, SuccessCallback, ErrorCallback){
		var jobName = this.jobName;
		$.ajax({
			url : this.serviceUrl,
			async : true,
			type : 'POST',
			data : jobParameters,
			success : function(xml) {
				var job = getJobFromXml(xml, jobName);
				SuccessCallback(job);
			},
			error : function(xhr, status, exception) {
				ErrorCallback(exception);
			},
			processData: false,  // tell jQuery not to process the data
			contentType: false   // tell jQuery not to set contentType
		});
	};
	uwsClient.prototype.destroyJob = function(id,successCallback, errorCallback) {
		var jobName = this.jobName;
		$.ajax({
			url : this.serviceUrl + "/" + id,
			type: 'POST',
			dataType: "xml",
			data: "ACTION=DELETE",
			success : function(xml) {
				var jobs = getJobListFromXml(xml, jobName);
				successCallback(id, jobs);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, exception);
			},
		});
		
	};
	uwsClient.prototype.abortJob = function(id, successCallback, errorCallback) {
		$.ajax({
			url : this.serviceUrl + "/" + id + "/phase",
			type: 'POST',
			dataType: "xml",
			data: "PHASE=ABORT",
			success : function(xml) {
				successCallback(id);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, exception);
			},
		});
		
	};
	uwsClient.prototype.startJob = function(id, successCallback, errorCallback) {
		$.ajax({
			url : this.serviceUrl + "/" + id + "/phase",
			type: 'POST',
			dataType: "xml",
			data: "PHASE=RUN",
			success : function(xml) {
				successCallback(id);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, exception);
			},
		});
		
	};
	
	uwsClient.prototype.getJobInfos = function(id,successCallback, errorCallback) {
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
				errorCallback(id, exception);
			},
		});
	};
	uwsClient.prototype.getJobResults = function(id,successCallback, errorCallback) {
		$.ajax({
			url : this.serviceUrl + "/" + id + "/results",
			type: 'GET',
			dataType: "xml",
			success : function(xml) {
				var results = readResults(xml);
				successCallback(id, results);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, exception);
			},
		});
	};
	
	uwsClient.prototype.getJobPhase = function(id,successCallback, errorCallback) {
		$.ajax({
			url : this.serviceUrl + "/" + id + "/phase",
			type: 'GET',
			success : function(xhr) {
				successCallback(id, xhr);
			},
			error : function(xhr, status, exception) {
				errorCallback(id, exception);
			},
		});
	};
	
	
	
	uwsClient.prototype.getJobInfosSync = function(id){
		return $.ajax({
			url : this.serviceUrl + "/" + id,
			async : false,
			type: 'GET',
			dataType: "xml",
		}).responseXML;
	}
	
	uwsClient.prototype.getJobListSync = function(){
		return $.ajax({
			url : this.serviceUrl,
			async : false,
			type : 'GET',
			dataType: "xml",
		}).responseXML;
	}
	
	uwsClient.prototype.getJobListInfos = function (successCallback, errorCallback) {
		var jobList = []
		var jobSummaryList = getJobListFromXml(this.getJobListSync(), this.jobName);
		for (var i in jobSummaryList){
			var id = jobSummaryList[i].jobId;
			var job = getJobFromXml(this.getJobInfosSync(id), this.jobName);
			jobList.push(job);
//			jobList.push(getJobFromXml(this.getJobInfosSync(jobSummaryList[i].jobId)));
		}
		successCallback(jobList);
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



