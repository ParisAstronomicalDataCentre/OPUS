import os
from urllib.parse import urlparse

from settings_local import VAR_PATH, BASE_URL

curdir = os.path.dirname(__file__)
print(f"OPUS directory is: {curdir}")

# --- Configuration Variables ---
# Update these to match your setup
OPUS_ROOT = curdir
VAR_DIR = VAR_PATH if VAR_PATH.startswith("/") else OPUS_ROOT + "/" + VAR_PATH
LOGS_DIR = f"{VAR_DIR}/logs"
# pid file and temp dirs, so that nginx does not need root to write in its default paths
NGINX_DIR = f"{VAR_DIR}/nginx"
OPUS_CLIENT_PORT = 8080
OPUS_SERVER_PORT = 8082
server_name = f"{urlparse(BASE_URL).netloc}"

# Output path for nginx.conf
NGINX_CONF_PATH = f"{OPUS_ROOT}/nginx/nginx.conf"

# --- Generate nginx.conf ---
nginx_config = f"""pid       {NGINX_DIR}/nginx.pid;
error_log {LOGS_DIR}/nginx_error.log;

events {{
    worker_connections 1024;
}}

http {{
    # Access log (using variables)
    access_log {LOGS_DIR}/nginx_access.log combined;

    # Temp dirs (default ones may be owned by root/nobody)
    client_body_temp_path {NGINX_DIR}/client_body_temp;
    proxy_temp_path       {NGINX_DIR}/proxy_temp;
    fastcgi_temp_path     {NGINX_DIR}/fastcgi_temp;
    uwsgi_temp_path       {NGINX_DIR}/uwsgi_temp;
    scgi_temp_path        {NGINX_DIR}/scgi_temp;

    # Upstream definitions (uvicorn ports)
    upstream opus_client {{
        server 127.0.0.1:{OPUS_CLIENT_PORT};
    }}
    upstream opus_server {{
        server 127.0.0.1:{OPUS_SERVER_PORT};
    }}

    server {{

        listen 80;
        server_name {server_name};

        location = /favicon.ico {{
            proxy_pass http://opus_client/favicon.ico ;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
            expires 30d;
            add_header Cache-Control "public, no-transform";
        }}

        # Opus Client
        location /opus_client/ {{
            proxy_pass http://opus_client/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }}

        # Static files
        location /static/ {{
            proxy_pass http://opus_client/static/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }}

        # Opus Server
        location /opus_server/ {{
            proxy_pass http://opus_server/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }}

        location / {{
            return 301 /opus_client/;
        }}
    }}
}}
"""

# --- Write the config file ---
# Create the nginx directory if it doesn't exist
os.makedirs(os.path.dirname(NGINX_CONF_PATH), exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(NGINX_DIR, exist_ok=True)

# Write the config
with open(NGINX_CONF_PATH, "w") as f:
    f.write(nginx_config)

print(f"✅ nginx config generated at: {NGINX_CONF_PATH}")
