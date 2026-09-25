"""
Settings for the tests, set as environment variables before uws_server and uws_client are
imported (environment variables have priority over .env)

The tests use a temporary VAR_PATH (database, logs, jobs...), kept after the tests so that
the files can be checked: its path is given at the end, with the command to remove it.
"""

import json
import os
import socket
import tempfile
import threading
import time

import pytest

TEST_VAR_PATH = tempfile.mkdtemp(prefix="opus_test_")


def _free_port():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


# UWS server started by the live_server fixture, used by the client (proxy)
SERVER_PORT = _free_port()
SERVER_URL = f"http://localhost:{SERVER_PORT}"
# Simulated Identity Provider for the client (its network calls are replaced in the tests)
TEST_IDP = {
    "title": "TestIdP",
    "description": "",
    "url_logo": "",
    "url": "https://idp.test/.well-known/openid-configuration",
    "client_id": "opus-test",
    "client_secret": "test-client-secret",
    "scope": "openid email",
}

os.environ.update(
    {
        "OPUS_ENV_FILE": "",  # do not read the local .env (tests independent of the local settings)
        "OPUS_VAR_PATH": TEST_VAR_PATH,
        "OPUS_STORAGE_TYPE": "SQLite",
        "OPUS_LOG_FILE_SUFFIX": "_test",
        "OPUS_MANAGER": "",
        "OPUS_ALLOW_ANONYMOUS": "true",
        "OPUS_CHECK_PERMISSIONS": "false",
        "OPUS_CHECK_OWNER": "false",
        "OPUS_BASE_URL": SERVER_URL,
        "OPUS_UWS_SERVER_URL": SERVER_URL,
        "OPUS_UWS_CLIENT_ENDPOINT": "http://localhost",
        # secrets for the tests (the client does not start without them)
        "OPUS_ADMIN_TOKEN": "test-admin-token",
        "OPUS_JOB_EVENT_TOKEN": "test-job-event-token",
        "OPUS_MAINTENANCE_TOKEN": "test-maintenance-token",
        "OPUS_SECRET_KEY": "test-secret-key-for-the-client",
        "OPUS_SECURITY_PASSWORD_SALT": "test-salt",
        "OPUS_ADMIN_DEFAULT_PW": "test-admin-password",
        "OPUS_TESTUSER_DEFAULT_PW": "test-testuser-password",
        "OPUS_SECURITY_REGISTERABLE": "true",
        "OPUS_OIDC_IDPS": json.dumps([TEST_IDP]),
    }
)
print(f"\nPerforming tests in {TEST_VAR_PATH}")


@pytest.fixture(scope="session")
def live_server():
    """UWS server running in a thread (real HTTP requests, e.g. from the client proxy)"""
    import asgiref.wsgi
    import uvicorn

    from uws_server import uws_server

    app = asgiref.wsgi.WsgiToAsgi(uws_server.app)
    server = uvicorn.Server(uvicorn.Config(app, host="localhost", port=SERVER_PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield SERVER_URL
    server.should_exit = True
    thread.join(timeout=5)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_sep("-", "OPUS test files")
    terminalreporter.write_line(f"Test files (database, logs, jobs) kept in: {TEST_VAR_PATH}")
    terminalreporter.write_line(f"They can be removed with: rm -rf {TEST_VAR_PATH}")
    parent = os.path.dirname(TEST_VAR_PATH)
    terminalreporter.write_line(f"(or all test directories: rm -rf {parent}/opus_test_*)")
