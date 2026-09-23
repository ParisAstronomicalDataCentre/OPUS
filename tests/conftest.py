"""
Settings for the tests, set as environment variables before uws_server is imported
(environment variables have priority over .env and settings_local.py)
"""

import datetime as dt
import os

now_str = dt.datetime.now().isoformat().split(".")[0]

os.environ.update(
    {
        "OPUS_STORAGE_TYPE": "SQLite",
        "OPUS_SQLITE_FILE_NAME": f"job_database_test_{now_str}.db",
        "OPUS_LOG_FILE_SUFFIX": "_test_" + now_str,
        "OPUS_MANAGER": "",
        "OPUS_ALLOW_ANONYMOUS": "true",
        "OPUS_CHECK_PERMISSIONS": "false",
        "OPUS_CHECK_OWNER": "false",
    }
)
print("\nPerforming tests")
