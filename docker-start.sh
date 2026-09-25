#!/bin/bash
# Entry point of the Docker container (see Dockerfile.dist): runs the server, the client
# and nginx, from the OPUS directory (WORKDIR of the image). Outside Docker, use: just start
# Generate nginx.conf from the settings (environment variables), and create its dirs
uv run --no-sync python generate_nginx_config.py
uv run --no-sync uvicorn app_server:asgi_app --host 0.0.0.0 --port 8082 --workers 1 --root-path /opus_server &
uv run --no-sync uvicorn app_client:asgi_app --host 0.0.0.0 --port 8080 --workers 1 --root-path /opus_client &
nginx -g 'daemon off;' -c "$(pwd)/nginx/nginx.conf" &
# Exit as soon as one process stops, so that the container is restarted
wait -n
echo "A process stopped, exiting" >&2
exit 1
