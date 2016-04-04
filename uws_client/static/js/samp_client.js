/*!
 * Copyright (c) 2016 by Cyril Chauvin
 * Licensed under MIT
 */

var samp_client = ( function($) {
	"use strict";
    
	var jss = {}, metadata = {
		"samp.name": "UWS Server",
		"samp.description": "UWS Server",
		"samp.icon.url": "https://voparis-uws-test.obspm.fr/favicon.ico",
		"author.name": "Mathieu Servillat",
		"author.affiliation": "Observatoire de Paris, LUTH",
		"author.mail": "mathieu.servillat@obspm.fr"
			
	},
	connector = new samp.Connector("UWS Server", metadata, null),/* connection = null,*/ msgs;

	function connHandler(conn) {
//		connection = conn;
		var i;
		for ( i = 0; i < msgs.length; i = i + 1) {
			conn.notifyAll([msgs[i]]);
		}
	}

	function regErrorHandler(e) {
		alert("SAMP error, please check if a SAMP hub is running");
	}

	function send() {
		connector.runWithConnection(connHandler, regErrorHandler);
	}

	function unregister() {
		if (connector.connection) {
			connector.unregister();
		}
	}

	function samp_votable(votable_url, votable_name) {
		var msg = new samp.Message("table.load.votable", {
//			"table-id" : votable_id,
			"url" : votable_url,
			"name" : votable_name
		});
		msgs = [msg];
		send();
	}

	function samp_image(url) {
		var msg = new samp.Message("image.load.fits", {
			"url" : url
		});
		msgs = [msg];
		send();
	}

	function samp_spectrum(url) {
		var msg = new samp.Message("spectrum.load.ssa-generic", {
			//"meta" : {"Access.Format":access_format},
			"url" : url
		});
		msgs = [msg];
		send();
	}
	function samp_data(data){
		var i,msg;
		msgs = [];
		for (i=0;i<data.length;i=i+1){
			if (data[i].type === 'image'){
				msg = new samp.Message("image.load.fits", {
					"url" : data[i].access_url
//					"name" : "TEST"
				});
				msgs.push(msg);
			}
			else if (data[i].type === 'spectrum'){
				msg = new samp.Message("spectrum.load.ssa-generic", {
					"url" : data[i].access_url
//					"name" : 
				});
				msgs.push(msg);
			}
			else if (data[i].type === 'votable'){
				msg = new samp.Message("table.load.votable", {
					"url" : data[i].access_url
//					"name" : 
				});
				msgs.push(msg);
			}
			else if (data[i].type === 'fitstable'){
				msg = new samp.Message("table.load.fits", {
					"url" : data[i].access_url
//					"name" : 
				});
				msgs.push(msg);
			}
		}
		send();
	}
	
	$(window).unload(function() {
        unregister();
    });

	/* Exports. */
	jss.samp_votable = samp_votable;
	jss.samp_image = samp_image;
	jss.samp_spectrum = samp_spectrum;
	jss.samp_data = samp_data;
	jss.unregister = unregister;

	return jss;
})(jQuery);
