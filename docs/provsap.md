
Provenance service (ProvSAP)
============================

Service of an OPUS server, declared in its capabilities (`<server>/capabilities`) with:

* identifier: `https://opus-job-manager.readthedocs.io/#provsap`
* URL: `<server>/provsap`

The server gives the provenance of a job or of a result, as proposed by the IVOA Provenance Simple Access Protocol
(ProvSAP): the activities (jobs), the entities they used and generated (parameters, results), and the agents.

The provenance follows the [IVOA Provenance Data Model](https://www.ivoa.net/documents/ProvenanceDM/) (version
1.0), which extends the [W3C PROV](https://www.w3.org/TR/prov-overview/) data model
([PROV-DM](https://www.w3.org/TR/prov-dm/)) with the descriptions of the activities and entities and with their
configuration. It is given in the W3C PROV formats: [PROV-JSON](https://www.w3.org/submissions/prov-json/) and
[PROV-XML](https://www.w3.org/TR/prov-xml/), or as a graph (SVG or PNG image).

`GET <server>/provsap?ID=<identifier>` with the parameters:

| Parameter | Value | Default |
| ---       | :---  | :---    |
| `ID` | Identifier of a job, or of an entity (result); may be repeated | required |
| `DEPTH` | Number of relations to follow from the identifier, or `ALL` | `1` |
| `DIRECTION` | `BACK` (what the job or entity comes from) or `FORWARD` (what was made from it) | `BACK` |
| `RESPONSEFORMAT` | `PROV-SVG` or `PROV-PNG` (graph, as an image), [`PROV-JSON`](https://www.w3.org/submissions/prov-json/) or [`PROV-XML`](https://www.w3.org/TR/prov-xml/) | `PROV-SVG` |
| `MODEL` | `IVOA` ([IVOA Provenance Data Model](https://www.ivoa.net/documents/ProvenanceDM/)) or `W3C` ([PROV-DM](https://www.w3.org/TR/prov-dm/) only) | `IVOA` |
| `AGENTS` | `1` or `0`: include the agents (owner of the job, contact of the job definition) | `1` |
| `MEMBERS` | `1` or `0`: include the members of the collections (parameter of ProvSAP, accepted but without effect in OPUS for now) | `0` |
| `DESCRIPTIONS` | `0`: no description, `1`: include the description of the activities (job definitions), `2`: also the descriptions of the entities and parameters | `0` |
| `CONFIGURATION` | `1` or `0`: include the configuration of the jobs (their parameters) | `1` |
| `ATTRIBUTES` | `1` or `0`: show the attributes of the elements and relations in the graph (`PROV-SVG`, `PROV-PNG`) | `1` |

The provenance of a single job is also given by `<server>/uws/<job name>/<job id>/provjson`, `provxml` and
`provsvg`.

The code is released under the MIT license.
