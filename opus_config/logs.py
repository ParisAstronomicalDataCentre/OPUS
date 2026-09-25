"""
Read the log files of the server and the client (log viewer of the client, for the admin)
"""

import os

LINES_DEFAULT = 100
LINES_MAX = 10000
BLOCK_SIZE = 65536


def log_files(log_path, prefix, suffix=""):
    """Log files of the server (prefix="server") or the client (prefix="client"): {name: path}
    (file names as in the logging configuration, see LOGGING in uws_server/settings.py and uws_client/settings.py)"""
    files = {prefix: f"{prefix}{suffix}.log", f"{prefix}_debug": f"{prefix}{suffix}_debug.log"}
    if prefix == "server":
        files["debug"] = f"debug{suffix}.log"  # other modules (e.g. libraries)
        # nginx in front of the server and the client (just start, Docker), see generate_nginx_config.py
        files["nginx_access"] = "nginx_access.log"
        files["nginx_error"] = "nginx_error.log"
    return {name: os.path.join(log_path, fname) for name, fname in files.items()}


def lines_param(value):
    """Number of lines requested, between 1 and LINES_MAX"""
    try:
        return min(max(int(value), 1), LINES_MAX)
    except (TypeError, ValueError):
        return LINES_DEFAULT


def tail(path, nlines=LINES_DEFAULT):
    """Last lines of a file, read from the end (the debug logs may be large)"""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        position = f.tell()
        data = b""
        # one more line than requested: the first one read may be incomplete
        while position > 0 and data.count(b"\n") <= nlines:
            size = min(BLOCK_SIZE, position)
            position -= size
            f.seek(position)
            data = f.read(size) + data
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[-nlines:]
