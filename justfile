default:
    @just --list

# Remove __pycache__ and .pyc files and folders
clean:
    @find . \( -name __pycache__ -o -name "*.pyc" \) -delete
    @echo 'python file cleaned ✅'

# Install python dependencies
install:
    @echo 'Install python dependancy:'
    @uv sync --no-dev
    @echo '✅'

# Install python with dev depenencies
install-dev:
    @echo 'Install python dev dependancies:'
    @uv sync
    @echo '✅'

# Black
black path="src":
    uv run black {{ path }}
    @echo 'black ✅'

# Lint type of python files with mypy
mypy path="src":
    uv run mypy --pretty {{ path }}
    @echo 'mypy ✅'

# Run the tests
test:
    uv run pytest -q tests

# Lint python files with ruff
ruff path="src":
    uv run ruff check {{ path }}
    @echo 'ruff ✅'

# Run OPUS server
server:
    uv run uvicorn app_server:asgi_app --host localhost --port 8082 --workers 1

# Run OPUS client
client:
    uv run uvicorn app_client:asgi_app --host localhost --port 8080 --workers 1

# Print a .env file with random secrets (e.g. just env > .env)
env template=".env.dist":
    @uv run python generate_env.py --template {{ template }}

# Generate nginx/nginx.conf from the settings (.env)
nginx_conf:
    uv run python generate_nginx_config.py

# Run OPUS server + client behind nginx (as local user, no sudo needed)
start:
    nginx -e stderr -c `pwd`/nginx/nginx.conf
    uv run uvicorn app_server:asgi_app --host localhost --port 8082 --workers 1 --root-path /opus_server &
    @sleep 1
    uv run uvicorn app_client:asgi_app --host localhost --port 8080 --workers 1 --root-path /opus_client &
    @sleep 1

stop:
    pkill -f uvicorn || true
    @sleep 1
    nginx -e stderr -c `pwd`/nginx/nginx.conf -s stop

# Maintenance of the jobs: update phases, archive expired jobs (from the server host, e.g. daily)
maintenance jobname="__all__" url="http://localhost:8082":
    @curl -sS --fail-with-body {{ url }}/handler/maintenance/{{ jobname }}

docker_build:
    docker build -t opus-app .

docker_run:
    docker run -p 80:80 --env-file .env.docker --add-host="opus-docker.localhost:127.0.0.1" --name opus-container opus-app &

docker_rm_all:
    docker stop $(docker ps -a -q)
    docker rm $(docker ps -a -q)
