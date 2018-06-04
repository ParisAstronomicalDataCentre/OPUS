#!/home/mservillat/anaconda/envs/wsgi/bin/python2.7

import os
import signal
import time
from uws import UWS
import subprocess as sp

url = "http://localhost/rest/dummy"
user_name = "anonymous"
password = "anonymous"
uws_client = UWS.client.Client(url=url)  # , user=user_name, password=password)

# curl -d "input=Hello World" $URL/rest/dummy

# Create dummy job with default parameters
def create_job():
    job = uws_client.new_job({'run_id': 'test'})
    job = uws_client.run_job(job.job_id)
    pid = int(job.job_info[0].text)
    print('Job created and started: PHASE={}, pid={}'.format(job.phase, pid))
    return job, pid

# create job
job, pid = create_job()

time.sleep(2)
phase = uws_client.get_phase(job.job_id)
print('Job phase: {}'.format(phase))
print('Testing SIGINT')
os.system("sudo -u _www kill {}".format(pid))

while phase not in ['ERROR', 'COMPLETED']:
    time.sleep(2)
    phase = uws_client.get_phase(job.job_id)
    print('Job phase: {}'.format(phase))

print(uws_client.get_job(job.job_id))
