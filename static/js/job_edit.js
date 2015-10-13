(function($) {
	"use strict";

    var jobname;
    var jobid;

    $(document).ready( function() {
    	// If tab is defined in div tab, show the requested tab
		//var tab = $('#tab').attr('value');
    	//if (tab) {
    	//	$('#myTab a[href="#'+tab+'"]').tab('show');
    	//}
    	$('#form-buttons').remove();
    	jobid = $('#jobid').attr('value');
    	jobname = $('#jobname').attr('value');
    	if (jobname && jobid) {
    		uws_manager.initManager([jobname]);
	    	uws_manager.displaySingleJob(jobname, jobid);
    	};
    });

})(jQuery);
