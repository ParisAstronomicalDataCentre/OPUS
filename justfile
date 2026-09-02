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

nginx_conf:
    uv run python generate_nginx_config.py

start:
    uv run uvicorn app_server:asgi_app --host localhost --port 8082 --workers 1 --root-path /opus_server &
    @sleep 1
    uv run uvicorn app_client:asgi_app --host localhost --port 8080 --workers 1 --root-path /opus_client &
    @sleep 1
    sudo nginx -c `pwd`/nginx/nginx.conf

stop:
    pkill -f uvicorn || true
    @sleep 1
    sudo nginx -s stop
