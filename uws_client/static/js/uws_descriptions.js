/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

/*
 * Built-in job descriptions, for the job lists of UWS services that are not OPUS servers (no job definitions,
 * /jdl), e.g. the asynchronous queries of a TAP server (the server is set in the Client Preferences, see the
 * Admin guide).
 *
 * The descriptions are in uws_descriptions.json (next to this file, loaded when first needed):
 *   {"tap": {"standard_id": "ivo://ivoa.net/std/TAP", "jobname": "async", ...}, ...}
 *   standard_id: standard of the service, as declared in its capabilities (<service URL>/capabilities, VOSI)
 *   jobname: name of the job list of such a service (<service URL>/<jobname>, e.g. async for TAP)
 * and the content of a job definition of OPUS (JSON of /jdl/<jobname>/json), used to build the form to create a
 * job and to describe the parameters of a job:
 *   parameters: {name: {datatype, default, required ("true" or "false"), annotation (HTML), options ("a,b,c"),
 *               widget ("textarea" for a long text), min, max}}
 *   parameters_keys: order of the parameters
 *   used, generated, control_parameters and their _keys: empty for an external service
 *   results: how to name the results of a job, when the service gives no type or name for them
 *     format_parameters: parameters of the job giving the format of its results (first one with a value)
 *     default_mimetype: type of the results if no format is given
 *     extensions: {mimetype: extension of the file}
 *   output_formats: [{mime, names}] formats of the service (set from its capabilities), to find the type of the
 *     results from the value of the format parameter (a type, or a short name)
 *
 * A description is found from the capabilities of the service (standard_id), and is then completed with them
 * (e.g. for TAP: query languages, output formats, limits), or if the capabilities are not available, from the
 * name of the job list (jobname).
 * With a description, jobs can be created and started (not aborted, deleted or run again). Without description,
 * the jobs of an external service are only listed and shown (read-only).
 *
 *   uwsDescriptions.find(serviceUrl, jobName, function (found) { ... });
 *     serviceUrl: URL of the service (with its endpoint, through the proxy of the client)
 *     jobName: name of the job list, or null to get the job list of the service from its capabilities
 *     found: {jobname, description, standard (true if found in the capabilities)}, or null
 */
var uwsDescriptions = (function() {
    "use strict";

    // uws_descriptions.json, in the directory of this script (same version parameter)
    var url = document.currentScript.src.replace(/uws_descriptions\.js/, 'uws_descriptions.json');

    // Descriptions, loaded when first needed (none if the file cannot be loaded)
    var loaded = null;
    function load() {
        if (!loaded) {
            loaded = fetch(url)
                .then(function (response) { return response.ok ? response.json() : {}; })
                .catch(function (error) {
                    console.log('Cannot load ' + url + ': ' + error);
                    return {};
                });
        }
        return loaded;
    }

    // Capabilities of a service (XML document, null if not available), asked once per service
    var capabilities = {};
    function getCapabilities(serviceUrl) {
        if (!capabilities[serviceUrl]) {
            capabilities[serviceUrl] = fetch(serviceUrl + '/capabilities')
                .then(function (response) { return response.ok ? response.text() : null; })
                .then(function (text) {
                    if (!text) {
                        return null;
                    }
                    var doc = new DOMParser().parseFromString(text, 'application/xml');
                    return doc.getElementsByTagName('parsererror').length ? null : doc;
                })
                .catch(function () { return null; });
        }
        return capabilities[serviceUrl];
    }

    // Capability of a standard in the capabilities of a service (element, or null)
    function findCapability(doc, standard_id) {
        var elements = doc ? doc.getElementsByTagNameNS('*', 'capability') : [];
        for (var i = 0; i < elements.length; i++) {
            var id = (elements[i].getAttribute('standardID') || '').toLowerCase();
            if (id == standard_id.toLowerCase()) {
                return elements[i];
            }
        }
        return null;
    }

    // Texts of the child elements with this name
    function texts(element, name) {
        return Array.from(element.children)
            .filter(function (child) { return child.localName == name; })
            .map(function (child) { return child.textContent.trim(); });
    }
    function children(element, name) {
        return Array.from(element.children).filter(function (child) { return child.localName == name; });
    }

    // Description completed with the capabilities of the service, by standard
    var complete = {
        // TAP (TAPRegExt): query languages, output formats, limits of the result, uploads
        'ivo://ivoa.net/std/tap': function (description, capability) {
            var params = description.parameters;
            // LANG: languages of the server, and their versions (e.g. ADQL, ADQL-2.0, ADQL-2.1)
            var languages = [];
            children(capability, 'language').forEach(function (language) {
                var name = texts(language, 'name')[0];
                if (name) {
                    languages.push(name);
                    texts(language, 'version').forEach(function (version) {
                        languages.push(name + '-' + version);
                    });
                }
            });
            if (params.LANG && languages.length) {
                params.LANG.options = languages.join(',');
                params.LANG.default = languages[0];
            }
            // RESPONSEFORMAT: formats of the server (short name if any), empty for the default of the server
            var formats = [];
            children(capability, 'outputFormat').forEach(function (format) {
                var names = texts(format, 'alias').filter(function (alias) { return alias.indexOf('/') == -1; });
                var name = names.length ? names[names.length - 1] : texts(format, 'mime')[0];
                if (name && name.indexOf(',') == -1 && formats.indexOf(name) == -1) {
                    formats.push(name);
                }
            });
            // (types and names of the formats, to find the type of the results of a job)
            description.output_formats = children(capability, 'outputFormat').map(function (format) {
                var mime = texts(format, 'mime')[0] || '';
                return {mime: mime, names: [mime].concat(texts(format, 'alias'))};
            });
            if (params.RESPONSEFORMAT && formats.length) {
                params.RESPONSEFORMAT.options = [''].concat(formats).join(',');
                params.RESPONSEFORMAT.annotation = 'Format of the result (default of the server if empty)';
            }
            // MAXREC: default and limit of the server
            var limit = children(capability, 'outputLimit')[0];
            if (params.MAXREC && limit) {
                var def = texts(limit, 'default')[0], hard = texts(limit, 'hard')[0];
                var info = [];
                if (def) { info.push('default: ' + def); }
                if (hard) { info.push('limit: ' + hard); params.MAXREC.max = hard; }
                if (info.length) {
                    params.MAXREC.annotation = 'Maximum number of rows of the result (' + info.join(', ') + ')';
                }
            }
            // UPLOAD: only if the server accepts uploads
            if (params.UPLOAD && children(capability, 'uploadMethod').length == 0) {
                delete params.UPLOAD;
                description.parameters_keys = description.parameters_keys.filter(function (key) { return key != 'UPLOAD'; });
            }
            // limits of the jobs, in the description of the service
            var duration = children(capability, 'executionDuration')[0];
            var retention = children(capability, 'retentionPeriod')[0];
            var limits = [];
            if (duration && texts(duration, 'default')[0]) {
                limits.push('execution limited to ' + texts(duration, 'default')[0] + ' s');
            }
            if (retention && texts(retention, 'default')[0]) {
                limits.push('jobs kept ' + Math.round(texts(retention, 'default')[0] / 3600) + ' h');
            }
            if (limits.length) {
                description.annotation += ' (' + limits.join(', ') + ')';
            }
            return description;
        }
    };

    function copy(description) {
        return JSON.parse(JSON.stringify(description));
    }

    // Find the description of a job list of a service, see above
    function find(serviceUrl, jobName, callback) {
        Promise.all([load(), getCapabilities(serviceUrl)]).then(function (results) {
            var descriptions = results[0], doc = results[1];
            var keys = Object.keys(descriptions);
            var i, description, capability;
            // from the capabilities of the service
            for (i = 0; i < keys.length; i++) {
                description = descriptions[keys[i]];
                capability = description.standard_id ? findCapability(doc, description.standard_id) : null;
                if (capability && (!jobName || jobName == description.jobname)) {
                    description = copy(description);
                    var completion = complete[description.standard_id.toLowerCase()];
                    if (completion) {
                        try {
                            description = completion(description, capability);
                        } catch (e) {
                            console.log('Capabilities not used for ' + keys[i] + ': ' + e);
                            description = copy(descriptions[keys[i]]);
                        }
                    }
                    callback({jobname: description.jobname, description: description, standard: true});
                    return;
                }
            }
            // from the name of the job list (capabilities not available)
            for (i = 0; i < keys.length; i++) {
                description = descriptions[keys[i]];
                if (jobName && !doc && jobName == description.jobname) {
                    callback({jobname: description.jobname, description: copy(description), standard: false});
                    return;
                }
            }
            callback(null);
        });
    }

    return {find: find};
})();
