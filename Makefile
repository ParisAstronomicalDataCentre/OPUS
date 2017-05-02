WWWUSER ?= www

init:
	mkdir -p var_data/logs
	mkdir -p var_data/db
	mkdir -p data/job_def
	mkdir -p data/job_def/scripts
	mkdir -p data/job_def/wadl
	mkdir -p data/job_def/votable
	mkdir -p var_data/jobdata
	mkdir -p var_data/sbatch
	mkdir -p var_data/uploads
	chown -R $(WWWUSER) var_data
	chown -R $(WWWUSER) uws_client/cork_conf

test:
	./test.py
