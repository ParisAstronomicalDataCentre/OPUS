#!/bin/sh
uv run uvicorn app_server:asgi_app --host 0.0.0.0 --port 8082 --workers 1 --root-path /opus_server &
uv run uvicorn app_client:asgi_app --host 0.0.0.0 --port 8080 --workers 1 --root-path /opus_client &
nginx -g 'daemon off;' -c /opt/opus/nginx/nginx.conf &
wait
