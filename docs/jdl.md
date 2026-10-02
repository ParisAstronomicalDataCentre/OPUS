
Job definitions service
=======================

Service of an OPUS server, declared in its capabilities (`<server>/capabilities`) with:

* identifier: `https://opus-job-manager.readthedocs.io/#jdl`
* URL: `<server>/jdl`

A job definition describes a job that the server can run: its parameters, the data it uses and generates, its
execution duration, and the script to run. The definitions are stored as
[VOTable](https://www.ivoa.net/documents/VOTable/) files, and are based on two IVOA Recommendations:

* the ActivityDescription class of the [IVOA Provenance Data Model](https://www.ivoa.net/documents/ProvenanceDM/)
  (version 1.0), with its parameters and the descriptions of the entities used and generated,
* the service descriptors of [IVOA DataLink](https://www.ivoa.net/documents/DataLink/) (version 1.1), a VOTable
  resource describing a service and its input parameters.

| Request | Response |
| ---     | :---     |
| `GET <server>/jdl` | The job definitions the user can access (JSON): `jobnames` (list of names), `details` (content of each definition) and `dates` (date of validation of each definition) |
| `GET <server>/jdl/<job name>/json` | The content of a job definition (JSON): parameters, used and generated entities, execution duration, contact... |
| `GET <server>/jdl/<job name>` | The job definition as a file (VOTable) |
| `GET <server>/jdl/<job name>/script` | The script of the job |

The UWS job list of a job definition is `<server>/uws/<job name>`. The job definitions are created and validated
with the client (see the [User guide](user_guide.md) and the [Admin guide](admin_guide.md)).


Content of a job definition file
--------------------------------

A job definition is a VOTable file with one `RESOURCE` element and no table, as a DataLink service descriptor.
The `utype` attributes give the classes and attributes of the Provenance Data Model (`voprov:`) and of UWS (`uws:`).

`RESOURCE` (`type="meta"`, `utype="voprov:ActivityDescription"`): the job definition, with the name of the job in
its `ID` and `name` attributes. It contains:

* `DESCRIPTION`: the description of the job.
* `PARAM` elements for the attributes of the job:

    | `name` | Content | `utype` |
    | ---    | :---    | :---    |
    | `doculink` | URL of the documentation of the job | `voprov:ActivityDescription.doculink` |
    | `type`, `subtype` | Type and subtype of the activity (e.g. `test`, `simulation`) | `voprov:ActivityDescription.type`, `.subtype` |
    | `version` | Version of the job definition | `voprov:ActivityDescription.version` |
    | `contact_name`, `contact_email` | Person or organization responsible for the job | `voprov:Agent.name`, `voprov:Agent.email` |
    | `executionDuration` | Maximum execution duration of a job, in seconds | `uws:Job.executionDuration` |
    | `quote` | Expected duration of a job, in seconds | `uws:Job.quote` |
    | `script` | Script run by the job (the parameters, inputs and results are shell variables, e.g. `$text`) | |

* `GROUP name="InputParams"`: the parameters of the job, one `PARAM` each (as in a service descriptor), with:
    * `ID` and `name`: the name of the parameter, `value`: its default value,
    * `datatype` (and `arraysize="*"` for a text): the type of the parameter; a file is a `char` with
      `xtype="application/octet-stream"`,
    * `type="no_query"`: the parameter is optional (it is required otherwise),
    * `unit`, `ucd`, `utype`: optional attributes,
    * `DESCRIPTION`: the description of the parameter,
    * `VALUES`: optional limits (`MIN`, `MAX`) or list of possible values (`OPTION`).

* `GROUP name="Used"`: the input data of the job, one `GROUP` (`utype="voprov:UsedDescription"`) each, named after
  the input, with a `DESCRIPTION` and the `PARAM` elements:

    | `name` | Content | `utype` |
    | ---    | :---    | :---    |
    | `role` | Role of the entity for the job | `voprov:UsedDescription.role` |
    | `multiplicity` | Number of entities expected | `voprov:UsedDescription.multiplicity` |
    | `default` | Default value (file name or identifier) | `voprov:Entity.id` |
    | `content_type` | Type of content (e.g. `image/fits`) | `voprov:EntityDescription.content_type` |
    | `url` | `file://$ID` for an uploaded file, or URL to get the data from its identifier (`$ID`) | `voprov:EntityDescription.url` |

* `GROUP name="Generated"`: the results of the job, one `GROUP` (`utype="voprov:WasGeneratedBy"`) each, named after
  the result, with a `DESCRIPTION` and the `PARAM` elements `role`, `multiplicity`
  (`voprov:WasGeneratedByDescription.role`, `.multiplicity`), `default` (name of the file written by the job,
  `voprov:Entity.id`) and `content_type` (`voprov:EntityDescription.content_type`).

Example (job `test_activity_2`, provided with OPUS in `test_jobs/`): a job with a text parameter and an input file,
that writes a text file.

```xml
<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3" version="1.3">
  <RESOURCE ID="test_activity_2" name="test_activity_2" type="meta" utype="voprov:ActivityDescription">
    <DESCRIPTION>Job for tests, simply adds input text to a given file</DESCRIPTION>
    <PARAM name="doculink" value="" arraysize="*" datatype="char" utype="voprov:ActivityDescription.doculink"/>
    <PARAM name="type" value="test" arraysize="*" datatype="char" utype="voprov:ActivityDescription.type"/>
    <PARAM name="subtype" value="test" arraysize="*" datatype="char" utype="voprov:ActivityDescription.subtype"/>
    <PARAM name="version" value="1" arraysize="*" datatype="char" utype="voprov:ActivityDescription.version"/>
    <PARAM name="contact_name" value="opus-admin" arraysize="*" datatype="char" utype="voprov:Agent.name"/>
    <PARAM name="contact_email" value="admin@opus" arraysize="*" datatype="char" utype="voprov:Agent.email"/>
    <PARAM name="executionDuration" value="20" datatype="int" utype="uws:Job.executionDuration"/>
    <PARAM name="quote" value="10" datatype="int" utype="uws:Job.quote"/>
    <PARAM name="script" value="sleep 5&#13;&#10;cat $input &gt; $output&#13;&#10;echo $text &gt;&gt; $output&#13;&#10;"
           arraysize="*" datatype="char"/>
    <GROUP name="InputParams">
      <PARAM ID="text" name="text" datatype="char" value="!" arraysize="*">
        <DESCRIPTION>Input text for test job 2</DESCRIPTION>
      </PARAM>
    </GROUP>
    <GROUP name="Used">
      <GROUP name="input" utype="voprov:UsedDescription">
        <DESCRIPTION>Input entity for test job 2</DESCRIPTION>
        <PARAM name="role" value="" arraysize="*" datatype="char" utype="voprov:UsedDescription.role"/>
        <PARAM name="multiplicity" value="" arraysize="*" datatype="char" utype="voprov:UsedDescription.multiplicity"/>
        <PARAM name="default" value="input.txt" arraysize="*" datatype="char" utype="voprov:Entity.id"/>
        <PARAM name="content_type" value="" arraysize="*" datatype="char" utype="voprov:EntityDescription.content_type"/>
        <PARAM name="url" value="file://$ID" arraysize="*" datatype="char" utype="voprov:EntityDescription.url"/>
      </GROUP>
    </GROUP>
    <GROUP name="Generated">
      <GROUP name="output" utype="voprov:WasGeneratedBy">
        <DESCRIPTION>Output file that contains the input file and input text</DESCRIPTION>
        <PARAM name="role" value="" arraysize="*" datatype="char" utype="voprov:WasGeneratedByDescription.role"/>
        <PARAM name="multiplicity" value="" arraysize="*" datatype="char" utype="voprov:WasGeneratedByDescription.multiplicity"/>
        <PARAM name="default" value="output.txt" arraysize="*" datatype="char" utype="voprov:Entity.id"/>
        <PARAM name="content_type" value="text/plain" arraysize="*" datatype="char" utype="voprov:EntityDescription.content_type"/>
      </GROUP>
    </GROUP>
  </RESOURCE>
</VOTABLE>
```
