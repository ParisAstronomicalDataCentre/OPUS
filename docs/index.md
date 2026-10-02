
Overview
========

**OPUS** (**O**bservatoire de **P**aris **U**WS **S**ystem) is a job control 
system developed using the micro-framework bottle.py. The Universal Worker System 
pattern v1.1 (UWS) as defined by the International Virtual Observatory Alliance 
(IVOA) is implemented as a REST service to control job execution on a work cluster.
OPUS also follows the proposed IVOA Provenance Data Model to capture and expose 
the provenance information of jobs and results.

More information on the UWS pattern recommendation can be found 
[here](http://www.ivoa.net/documents/UWS/).

More information on the IVOA Provenance Data Model can be found 
[here](http://www.ivoa.net/documents/ProvenanceDM/).

The **UWS server** is a web application composed of:

* a REST interface following the bottle.py framework to implement the UWS pattern,

* a set of classes to define, create and manage UWS jobs and job lists,

* Storage classes to store job properties in a database (based on SQLAlchemy),

* Manager classes to communicate with a work cluster (currently the
  Local and SLURM manager classes are available),

* Job description language (JDL) functions to read and write job descriptions
  following the IVOA Provenance data model.

The **UWS client** is mainly based on the JavaScript library `uwsLib.js` that can be
used independently to send requests to the server. The core of the client is the
`uws_client.js` file that is used to create requests, parse responses, and then
display job lists and job properties in web pages. 

A set of HTML pages use those scripts and are exposed by a web service based on the 
Flask framework (though the scripts can be integrated to any other web service).  
Note that the UWS client also uses the JavaScript frameworks [Bootstrap 5](http://getbootstrap.com/) 
and [jQuery](https://jquery.com/), they are provided with the client.


Services of an OPUS server
--------------------------

An OPUS server lists its services in its capabilities (`<server>/capabilities`, IVOA Support Interfaces), each with
an identifier and its URL:

* the UWS job lists, with the identifier defined by the IVOA (`ivo://ivoa.net/std/UWS#rest-1.1`),
* <a id="jdl"></a>the [job definitions](jdl.md) (`https://opus-job-manager.readthedocs.io/#jdl`),
* <a id="provsap"></a>the [provenance of the jobs](provsap.md), following the IVOA ProvSAP proposal
  (`https://opus-job-manager.readthedocs.io/#provsap`).
