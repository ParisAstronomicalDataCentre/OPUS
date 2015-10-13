(function($) {
	"use strict";

    var jobName = 'ctbin';
    var newJobParams = {};

    $(document).ready( function() {
    	
 	    // Look at URL to set jobName
    	jobName = location.pathname.split('/').pop();
 	    
 	    // Look at GET parameters to fill newJobParams
    	var updateNewJobParams = function(form_params) {    	
        	var pairs = form_params.split('&'); //window.location.search.substring(1).split('&');
        	for (var i in pairs) {
        		var pair = pairs[i].split('=');
        		var key = decodeURIComponent(pair[0]);
        		var val = decodeURIComponent(pair[1]);
        		switch (key) {
        			case 'csrfmiddlewaretoken': break;
        			case 'evfile':
                    	logger('WARNING', 'DEBUG mode: set evfile=http://voplus.obspm.fr/cta/events.fits');
        				newJobParams['evfile'] = 'http://voplus.obspm.fr/cta/events.fits';
        				break;
                    default:
                    	newJobParams[key] = val;
            	};
        	};
		};
        
        var createNewJob = function() {
	    	// Creation of a new job and display results
	    	newJobParams['PHASE'] = 'RUN';
	    	//uws_client.createClient(serviceUrl, jobName);
	    	//uws_client.createJob(newJobParams);
    		uws_manager.initManager([jobName]);			
	    	uws_manager.createJob(jobName, newJobParams);
    	};

    	// catch the form's submit event to validate form
        $('#job_params').submit(function() {
            $.ajax({ // create an AJAX call...
                data: $(this).serialize(), // get the form data
                type: $(this).attr('method'), // GET or POST
                url: $(this).attr('action'), // the url to call, here: job_send
                success: function(response) { // on success..
                    $('#job_params').html(response); // update the DIV with new form
                    if ($('#job_params div').hasClass('has-error')) {
                    	logger('DEBUG', 'createJob form has errors!');
                    } else {
                    	logger('DEBUG', 'createJob form is valid!');
                    	updateNewJobParams($('#job_params').serialize());
                    	createNewJob();
                    };
                }
            });
            return false; // cancel original event to prevent form submitting
        });	    

    });
        
})(jQuery);
