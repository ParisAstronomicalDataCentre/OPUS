req:
    pip install -r requirements.txt

init:
    mkdir data/db
    mkdir data/job_def
    mkdir data/job_def/scripts
    mkdir data/job_def/wadl
    mkdir data/jobdata
    mkdir data/sbatch
    mkdir data/uploads
    chown -R www:www data
    chown -R www:www uws_client/cork_conf

test:
    ./test.py