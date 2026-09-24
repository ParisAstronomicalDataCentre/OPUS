"""
Settings for the tests, set as environment variables before uws_server is imported
(environment variables have priority over .env)

The tests use a temporary VAR_PATH (database, logs, jobs...), kept after the tests so that
the files can be checked: its path is given at the end, with the command to remove it.
"""

import os
import tempfile

TEST_VAR_PATH = tempfile.mkdtemp(prefix="opus_test_")

os.environ.update(
    {
        "OPUS_VAR_PATH": TEST_VAR_PATH,
        "OPUS_STORAGE_TYPE": "SQLite",
        "OPUS_LOG_FILE_SUFFIX": "_test",
        "OPUS_MANAGER": "",
        "OPUS_ALLOW_ANONYMOUS": "true",
        "OPUS_CHECK_PERMISSIONS": "false",
        "OPUS_CHECK_OWNER": "false",
    }
)
print(f"\nPerforming tests in {TEST_VAR_PATH}")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_sep("-", "OPUS test files")
    terminalreporter.write_line(f"Test files (database, logs, jobs) kept in: {TEST_VAR_PATH}")
    terminalreporter.write_line(f"They can be removed with: rm -rf {TEST_VAR_PATH}")
    parent = os.path.dirname(TEST_VAR_PATH)
    terminalreporter.write_line(f"(or all test directories: rm -rf {parent}/opus_test_*)")
