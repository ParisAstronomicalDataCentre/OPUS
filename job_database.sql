-- DROP TABLE jobs;
-- DROP TABLE job_parameters;
-- DROP TABLE job_results;

CREATE TABLE jobs (
    jobid              varchar(36) not null,
    jobname            varchar(255) not null,
    phase              varchar(10) not null,
    quote              int,
    execution_duration int,
    error              varchar(255),
    start_time         timestamp,
    end_time           timestamp,
    destruction_time   timestamp,
    owner              varchar(64),
    run_id             int,
    CONSTRAINT pk_jobs PRIMARY KEY (jobid)
);

CREATE TABLE job_parameters (
    jobid varchar(36) not null,
    name  varchar(255),
    value varchar(255),
    byref boolean default False,
    CONSTRAINT pk_job_parameters PRIMARY KEY (jobid, name)
);

CREATE TABLE job_results (
    jobid varchar(36) not null,
    name  varchar(255),
    url   varchar(255),
    CONSTRAINT pk_job_results PRIMARY KEY (jobid, name)
);

INSERT INTO jobs (jobid, jobname, phase, quote, execution_duration, error, start_time, end_time, destruction_time, owner, run_id) VALUES ('426b0286-e656-b924-c14a-fbd02f9ebaa9', 'ctbin', 'COMPLETED', NULL, 86400, NULL, '2015-02-25 12:06:24', '2015-02-25 12:06:58', '2015-03-04 12:06:20', 'anonymous', NULL);
INSERT INTO job_parameters (jobid, name, value) VALUES ('426b0286-e656-b924-c14a-fbd02f9ebaa9', 'evfile', 'http://voplus.obspm.fr/cta/events.fits');
INSERT INTO job_parameters (jobid, name, value) VALUES ('426b0286-e656-b924-c14a-fbd02f9ebaa9', 'enumbins', '1');
INSERT INTO job_results (jobid, name, url) VALUES ('426b0286-e656-b924-c14a-fbd02f9ebaa9', '0', 'http://voparis-uws.obspm.fr/data/uwsdata/644029/results/outfile.fits');
INSERT INTO job_results (jobid, name, url) VALUES ('426b0286-e656-b924-c14a-fbd02f9ebaa9', '1', 'http://voparis-uws.obspm.fr/data/uwsdata/644029/results/ctbin.log');

INSERT INTO jobs (jobid, jobname, phase, quote, execution_duration, error, start_time, end_time, destruction_time, owner, run_id) VALUES ('6ce13bc5-dbf3-6b04-b1e7-28d47ad32794', 'ctbin', 'PENDING', NULL, 86400, NULL, '2015-02-25 12:06:24', '2015-02-25 12:06:58', '2015-03-04 12:06:20', 'anonymous', NULL);
INSERT INTO job_parameters (jobid, name, value) VALUES ('6ce13bc5-dbf3-6b04-b1e7-28d47ad32794', 'evfile', 'http://voplus.obspm.fr/cta/events.fits');
INSERT INTO job_parameters (jobid, name, value) VALUES ('6ce13bc5-dbf3-6b04-b1e7-28d47ad32794', 'enumbins', '1');
INSERT INTO job_results (jobid, name, url) VALUES ('6ce13bc5-dbf3-6b04-b1e7-28d47ad32794', '0', 'http://voparis-uws.obspm.fr/data/uwsdata/644029/results/outfile.fits');
INSERT INTO job_results (jobid, name, url) VALUES ('6ce13bc5-dbf3-6b04-b1e7-28d47ad32794', '1', 'http://voparis-uws.obspm.fr/data/uwsdata/644029/results/ctbin.log');


