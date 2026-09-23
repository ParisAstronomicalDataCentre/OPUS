#!/bin/bash
mkdir -p /var/opt/opus/logs /var/opt/opus/nginx  # may be missing in an existing volume
uv run --no-sync uvicorn app_server:asgi_app --host 0.0.0.0 --port 8082 --workers 1 --root-path /opus_server &
uv run --no-sync uvicorn app_client:asgi_app --host 0.0.0.0 --port 8080 --workers 1 --root-path /opus_client &
nginx -g 'daemon off;' -c /opt/opus/nginx/nginx.conf &
# Exit as soon as one process stops, so that the container is restarted
wait -n
echo "A process stopped, exiting" >&2
exit 1
