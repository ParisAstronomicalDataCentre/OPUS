#!/home/mservillat/anaconda/envs/wsgi/bin/python2.7

from uws import UWS

url = "http://localhost/rest/dummy"
user_name = "anonymous"
password = "anonymous"
uws_client = UWS.client.Client(url=url)  # , user=user_name, password=password)

# curl -d "input=Hello World" $URL/rest/dummy

# Create dummy job with default parameters
job = uws_client.new_job()
job = uws_client.run_job(job.job_id)

# send kill signal to process
pid = job.job_info[0].text

