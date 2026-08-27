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
    conda deactivate
    uv run python run_server.py

# Run OPUS client
client:
    conda deactivate
    uv run python run_client.py

server_uvicorn:
    uv run uvicorn app_server:asgi_app --host localhost --port 8082 --workers 1

client_uvicorn:
    uv run uvicorn app_client:asgi_app --host localhost --port 8080 --workers 1

start:
    uv run uvicorn app_server:asgi_app --host localhost --port 8082 --workers 1 &
    uv run uvicorn app_client:asgi_app --host localhost --port 8080 --workers 1 &
    sudo

stop:
    pkill -f uvicorn
    sudo nginx -s stop
