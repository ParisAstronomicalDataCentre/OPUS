/*!
 * Copyright (c) 2016 by Cyril Chauvin
 * Licensed under MIT
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


	URL_TOPCAT = 'http://www.star.bris.ac.uk/~mbt/topcat/topcat-full.jnlp',
	URL_ALADIN = 'http://aladin.u-strasbg.fr/java/nph-aladin.pl?frame=get&id=aladin.jnlp',
	URL_CASSIS = "http://cassis.irap.omp.eu/online/cassis.jnlp",
	URL_MIZAR = 'http://voparis-srv-paris.obspm.fr/mizar/',
	URL_APERICUBES = "http://voparis-apericubes.obspm.fr/apericubes/js9/demo.php?samp_register=on",
	URL_AUTOPLOT = "http://autoplot.org/autoplot.jnlp",

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
		alert("SAMP error");
	}

	function sendMessage(conn, msgs) {
		var i;
		for (i = 0; i < msgs.length; i = i + 1) {
			conn.notifyAll([ msgs[i] ]);
		}
	}

	function waitForSampApplication(type, mtype, data, connHandler) {
		if (type == "subs" && (mtype in data)) {
			connector.runWithConnection(connHandler, regErrorHandler);
			return true;
		}
		return false;
	}

	function connect(connection, mtype, openDefaultApplication, connHandler) {
		connection.getSubscribedClients([ mtype ], function(idlist) {
			if (Object.keys(idlist).length == 0) {
				openDefaultApplication();
			} else {
				connector.runWithConnection(connHandler, regErrorHandler);
			}
		});
	}

	function startHub(onConnect, url_samphub) {
		$('<iframe>', {
			frameborder : 0,
			src : url_samphub,
			style : 'width:0; height:0;'
		}).appendTo('body');
		var waitingForHub = connector.onHubAvailability(function(res) {
			if (res) {
				clearInterval(waitingForHub);
				connector.runWithConnection(onConnect);
			}
		}, 3000);
	}

	var Sender = function(msgs, mtype, url_samphub, launchDefaultApplication) {
		this.msgs = msgs;
		this.mtype = mtype;
		this.url_samphub = url_samphub;
		this.launchDefaultApplication = launchDefaultApplication;
		this.sent = false;
		var self = this;
		this.connHandler = function(conn) {
			sendMessage(conn, self.msgs);
		};
		this.openDefaultApplication = function() {
			clientTracker.onchange = function(id, type, data) {
				if (!self.sent) {
					if (waitForSampApplication(type, self.mtype, data,
							self.connHandler)) {
						self.sent = true;
					}
				}
			};
			self.launchDefaultApplication();
		};

		this.onConnect = function(connection) {
			connect(connection, self.mtype, self.openDefaultApplication,
					self.connHandler);
		};
		this.send = function() {
			samp.ping(function(res) {
				if (res) {
					connector.runWithConnection(self.onConnect);
				} else {
					startHub(self.onConnect, self.url_samphub);
				}
			});
		};
	}

	function samp_votable(votable_url, votable_name) {
		var MSG = new samp.Message(MTYPE_VOTABLE, {
			"url" : votable_url,
			"name" : votable_name
		});
		var msgs = [ MSG ];
		var url_samphub = URL_TOPCAT;

		function launchDefaultApplication() {
			$('<iframe>', {
				frameborder : 0,
				src : URL_TOPCAT,
				style : 'width:0; height:0;'
			}).appendTo('body');
		}

		var sender = new Sender(msgs, MTYPE_VOTABLE, url_samphub,
				launchDefaultApplication);
		sender.send();
	}

	function samp_fits(fits_url, fits_name) {
		var MSG = new samp.Message(MTYPE_FITS, {
			"url" : fits_url,
			"name" : fits_name
		});
		var msgs = [ MSG ];
		var url_samphub = URL_TOPCAT;

		function launchDefaultApplication() {
			$('<iframe>', {
				frameborder : 0,
				src : URL_TOPCAT,
				style : 'width:0; height:0;'
			}).appendTo('body');
		}

		var sender = new Sender(msgs, MTYPE_VOTABLE, url_samphub,
				launchDefaultApplication);
		sender.send();
	}

	function samp_geojson(target_name, catalog_name, url) {

		var MSG = new samp.Message(MTYPE_GEOJSON, {
			"target_name" : target_name,
			"catalog_name" : catalog_name,
			"url" : url
		});
		var msgs = [ MSG ];

		var url_samphub = URL_TOPCAT;

		var launchDefaultApplication = function() {
			window.open(URL_MIZAR);
		}

		var sender = new Sender(msgs, MTYPE_GEOJSON, url_samphub,
				launchDefaultApplication);
		sender.send();
	}

	function samp_data(data) {
		var i, msg, mType, url_samphub, url_default_application, launchDefaultApplication, msgs = [];
		for (i = 0; i < data.length; i = i + 1) {
			var mType = null;
			switch (data[i].type) {
			case 'image':
				mType = MTYPE_FITS;
				url_samphub = URL_ALADIN;
				url_default_application = URL_ALADIN;
				break;
			case 'spectrum':
				mType = MTYPE_SPECTRUM;
				url_samphub = URL_CASSIS;
				url_default_application = URL_CASSIS;
				break;
			case 'votable':
				mType = MTYPE_VOTABLE;
				url_samphub = URL_TOPCAT;
				url_default_application = URL_TOPCAT;
				break;
			case 'cdf':
				mType = MTYPE_CDF;
				url_samphub = URL_TOPCAT;
				url_default_application = URL_TOPCAT;
				break;
			case 'pds_virtis_demo':
				mType = MTYPE_VIRTIS;
				url_samphub = URL_TOPCAT;
				url_default_application = URL_APERICUBES;
				break;
			case 'das2':
				mType = MTYPE_DAS2;
				url_samphub = URL_TOPCAT;
				url_default_application = URL_AUTOPLOT;
				break;
			}
			msg = new samp.Message(mType, {
				"url" : data[i].access_url
			});
			msgs.push(msg);
		}

		if (url_default_application != URL_APERICUBES) {
			launchDefaultApplication = function() {
				$('<iframe>', {
					frameborder : 0,
					src : url_default_application,
					style : 'width:0; height:0;'
				}).appendTo('body');
			}
		} else {
			launchDefaultApplication = function() {
				window.open(url_default_application);
			}
		}
		var sender = new Sender(msgs, mType, url_samphub,
				launchDefaultApplication);
		sender.send();

	}

	function samp_sregion(sregion_list) {
		var i, msg, msgs = [];
		var mType = MTYPE_SREGION;
		var url_samphub = URL_ALADIN;
		var url_default_application = URL_ALADIN;
		for (i = 0; i < sregion_list.length; i = i + 1) {
			msg = new samp.Message(mType, {
				"script" : sregion_list[i]
			});
			msgs.push(msg);
		}


		function launchDefaultApplication() {
			$('<iframe>', {
				frameborder : 0,
				src : URL_ALADIN,
				style : 'width:0; height:0;'
			}).appendTo('body');
		}

		var sender = new Sender(msgs, mType, url_samphub,
				launchDefaultApplication);
		sender.send();
	}

	$(window).unload(function() {
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
