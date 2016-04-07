
Overview
========
**OPUS** (**O**bservatoire de **P**aris **U**WS **S**ystem) is a job control 
system developed using the micro-framework bottle.py. The Universal Worker System 
pattern v1.0 (UWS) as defined by the International Virtual Observatory Alliance 
(IVOA) is implemented as a REST service to manage job execution on a work cluster.

More information on the UWS pattern recommendation can be found 
[here](http://www.ivoa.net/documents/UWS/20101010/).

The **UWS server** is a web application composed of:

* a REST interface following the bottle.py framework and the UWS recommendation,

* a set of classes to define, create and manage UWS jobs and job lists

* Storage classes to store job properties in a database (currently only the
  SQLiteStorage class is available),

* Manager classes to communicate with a work cluster (currently only the
  SLURMManager class is available),

* Job description language (JDL) functions to read and write descriptions
  (currently the WADL standard is used).

The **UWS client** is based on the JavaScript library `uwsLib.js` that can be
used independently to send requests to the server. The core of the client is the
`uws_manager.js` file that is used to create requests, parse responses, and then
display job lists and job properties in web pages.A set of HTML pages use those
scripts and are accessed through bottle.py functions. A separate web page allows
the user to create and modify job definitions. Note that the UWS client uses the
JavaScript frameworks [BootStrap3](http://getbootstrap.com/) and 
[jQuery](https://jquery.com/), they are thus requirements.

The code is released under the MIT license.
