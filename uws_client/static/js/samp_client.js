/*!
 * Copyright (c) 2016 by Cyril Chauvin
 * Licensed under MIT
 */

/*
 * Send files to desktop applications (e.g. TOPCAT, Aladin, DS9) with SAMP (Web Profile, see vendor/sampjs):
 *   samp_client.samp_fits(url, name)      FITS image
 *   samp_client.samp_votable(url, name)   VOTable
 * The SAMP hub runs on the computer of the user (started by TOPCAT or Aladin): if there is no hub, or no application
 * accepting the type of message, a message is shown (the applications are not started from the page).
 */
var samp_client = ( function($) {
	"use strict";

	var jss = {},
	metadata = {
		"samp.name": "OPUS",
		"samp.description": "OPUS - Observatoire de Paris UWS Server - http://opus-job-manager.readthedocs.io/",
		"samp.icon.url": "https://voparis-uws-test.obspm.fr/favicon.ico",
		"author.name": "Mathieu Servillat",
		"author.affiliation": "Observatoire de Paris, LUTH",
		"author.mail": "mathieu.servillat@obspm.fr"

	},
	MTYPE_VOTABLE = "table.load.votable",
	MTYPE_GEOJSON = "table.load.geojson",
	MTYPE_FITS = "image.load.fits",
	MTYPE_SPECTRUM = "spectrum.load.ssa-generic",
	MTYPE_CDF = "table.load.cdf",
	MTYPE_VIRTIS = 'table.load.pds-virtis-demo',
	MTYPE_SREGION = 'script.aladin.send',
	MTYPE_DAS2 = "table.load.das2",

	clientTracker = new samp.ClientTracker(),
	callableClient = {
			receiveNotification: function(senderId, message) {
				clientTracker.receiveNotification(senderId, message);
			},
		},
	subs = {"samp.hub.event.subscriptions": {}},
	connector = new samp.Connector(metadata["samp.name"], metadata, callableClient, subs);

	function unregister() {
		if (connector.connection) {
			connector.unregister();
		}
	}

	function regErrorHandler(e) {
		global.showMessage('SAMP: the connection to the hub failed or was refused', 'danger');
	}

	// Send the messages (of type mtype) to the applications connected to the SAMP hub
	function send(msgs, mtype) {
		samp.ping(function(hub_found) {
			if (!hub_found) {
				global.showMessage('SAMP: no hub found, start an application with a SAMP hub first (e.g. TOPCAT or Aladin)', 'warning');
				return;
			}
			connector.runWithConnection(function(connection) {
				connection.getSubscribedClients([ mtype ], function(idlist) {
					if (Object.keys(idlist).length == 0) {
						global.showMessage('SAMP: no application accepts this type of file (' + mtype + ')', 'warning');
						return;
					}
					for (var i = 0; i < msgs.length; i = i + 1) {
						connection.notifyAll([ msgs[i] ]);
					}
					global.showMessage('SAMP: sent to ' + Object.keys(idlist).length + ' application(s)', 'success');
				});
			}, regErrorHandler);
		});
	}

	function samp_votable(votable_url, votable_name) {
		send([ new samp.Message(MTYPE_VOTABLE, {"url" : votable_url, "name" : votable_name}) ], MTYPE_VOTABLE);
	}

	function samp_fits(fits_url, fits_name) {
		send([ new samp.Message(MTYPE_FITS, {"url" : fits_url, "name" : fits_name}) ], MTYPE_FITS);
	}

	function samp_geojson(target_name, catalog_name, url) {
		send([ new samp.Message(MTYPE_GEOJSON, {
			"target_name" : target_name,
			"catalog_name" : catalog_name,
			"url" : url
		}) ], MTYPE_GEOJSON);
	}

	// data: list of {type: image | spectrum | votable | cdf | pds_virtis_demo | das2, access_url: ...}
	// (the type of the messages is the one of the last item)
	function samp_data(data) {
		var mtypes = {
			'image': MTYPE_FITS,
			'spectrum': MTYPE_SPECTRUM,
			'votable': MTYPE_VOTABLE,
			'cdf': MTYPE_CDF,
			'pds_virtis_demo': MTYPE_VIRTIS,
			'das2': MTYPE_DAS2
		};
		var i, mType = null, msgs = [];
		for (i = 0; i < data.length; i = i + 1) {
			mType = mtypes[data[i].type] || null;
			msgs.push(new samp.Message(mType, {"url" : data[i].access_url}));
		}
		send(msgs, mType);
	}

	function samp_sregion(sregion_list) {
		var i, msgs = [];
		for (i = 0; i < sregion_list.length; i = i + 1) {
			msgs.push(new samp.Message(MTYPE_SREGION, {"script" : sregion_list[i]}));
		}
		send(msgs, MTYPE_SREGION);
	}

	$(window).on('beforeunload', function() {
		unregister();
	});

	/* Exports. */
	jss.samp_votable = samp_votable;
	jss.samp_fits = samp_fits;
	jss.samp_data = samp_data;
	jss.samp_geojson = samp_geojson;
	jss.samp_sregion = samp_sregion;
	jss.unregister = unregister;

	return jss;
})(jQuery);
