init:
	mkdir -p data/db
	mkdir -p data/job_def
	mkdir -p data/job_def/scripts
	mkdir -p data/job_def/wadl
	mkdir -p data/jobdata
	mkdir -p data/sbatch
	mkdir -p data/uploads
	chown -R www:www data
	chown -R www:www uws_client/cork_conf

test:
	./test.py
