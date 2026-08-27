import os

# --- Configuration Variables ---
# Update these to match your setup
OPUS_ROOT = "/Users/mservillat/Professionnel/GIT/OPUS"
LOGS_DIR = f"{OPUS_ROOT}/var/logs"
STATIC_DIR = f"{OPUS_ROOT}/uws_client/static"
OPUS_CLIENT_PORT = 8080
OPUS_SERVER_PORT = 8082

# Output path for nginx.conf
NGINX_CONF_PATH = f"{OPUS_ROOT}/nginx/nginx.conf"

# --- Generate nginx.conf ---
nginx_config = f"""events {{
    worker_connections 1024;
}}

http {{
    # Access and error logs (using variables)
    access_log {LOGS_DIR}/nginx_access.log combined;
    error_log  {LOGS_DIR}/nginx_error.log;

    # Upstream definitions (uvicorn ports)
    upstream opus_client {{
        server 127.0.0.1:{OPUS_CLIENT_PORT};
    }}
    upstream opus_server {{
        server 127.0.0.1:{OPUS_SERVER_PORT};
    }}

    server {{

        listen 80;
        server_name localhost;

        # Static files
        location /opus_client/static/ {{
            root {OPUS_ROOT}/uws_client;
            # alias {STATIC_DIR}/;
            expires 30d;
        }}

        # Opus Client
        location /opus_client/ {{
            proxy_pass http://opus_client/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }}

        # Opus Server
        location /opus_server/ {{
            proxy_pass http://opus_server/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }}
    }}
}}
"""

# --- Write the config file ---
# Create the nginx directory if it doesn't exist
os.makedirs(os.path.dirname(NGINX_CONF_PATH), exist_ok=True)

# Write the config
with open(NGINX_CONF_PATH, "w") as f:
    f.write(nginx_config)

print(f"✅ nginx config generated at: {NGINX_CONF_PATH}")
