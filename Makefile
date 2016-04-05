WWWUSER ?= www

init:
	mkdir -p data/db
	mkdir -p data/job_def
	mkdir -p data/job_def/scripts
	mkdir -p data/job_def/jdl
	mkdir -p data/jobdata
	mkdir -p data/sbatch
	mkdir -p data/uploads
	chown -R $(WWWUSER) data
	chown -R $(WWWUSER) uws_client/cork_conf

test:
	./test.py
