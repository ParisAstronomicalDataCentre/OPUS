
Overview
========
**OPUS** (**O**bservatoire de **P**aris **U**WS **S**ystem) is a job control 
system developed using the micro-framework bottle.py. The Universal Worker System 
pattern v1.0 (UWS) as defined by the International Virtual Observatory Alliance 
(IVOA) is implemented as a REST service to control job execution on a work cluster.
OPUS also follows the proposed IVOA Provenance Data Model to capture and expose 
the provenance information of jobs and results.

More information on the UWS pattern recommendation can be found 
[here](http://www.ivoa.net/documents/UWS/20101010/).

More information on the IVOA Provenance Data Model can be found 
[here](http://www.ivoa.net/documents/ProvenanceDM/20181011/).

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
Note that the UWS client also uses the JavaScript frameworks [BootStrap3](http://getbootstrap.com/) 
and [jQuery](https://jquery.com/), they are thus requirements.

The code is released under the MIT license.
