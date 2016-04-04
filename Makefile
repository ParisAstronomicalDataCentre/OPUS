ifndef wwwuser
wwwuser=www
endif

init:
	mkdir -p data/db
	mkdir -p data/job_def
	mkdir -p data/job_def/scripts
	mkdir -p data/job_def/wadl
	mkdir -p data/jobdata
	mkdir -p data/sbatch
	mkdir -p data/uploads
	chown -R $wwwuser:$wwwuser data
	chown -R $wwwuser:$wwwuser uws_client/cork_conf

test:
	./test.py
