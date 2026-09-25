#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Generate the content of a .env file for OPUS, printed on stdout (no file is written)

    python generate_env.py > .env
        from the template .env.dist, with random values for the secrets

    python generate_env.py --template .env.docker.dist > .env.docker
        same, from another template

    python generate_env.py --from settings_local.py > .env
        convert the values of a settings_local.py file (deprecated) to OPUS_* variables,
        and add the new required secrets
"""

import argparse
import importlib.util
import json
import os
import re
import secrets
import sys

from opus_config import APP_PATH, ClientSettings, ServerSettings

TEMPLATE = os.path.join(APP_PATH, ".env.dist")
# Secrets generated when empty in the template, or missing in settings_local.py
RANDOM_SECRETS = [
    "ADMIN_TOKEN",
    "JOB_EVENT_TOKEN",
    "MAINTENANCE_TOKEN",
    "SECRET_KEY",
    "SECURITY_PASSWORD_SALT",
    "ADMIN_DEFAULT_PW",
    "TESTUSER_DEFAULT_PW",
]
# Before .env, the client used this salt: it is kept when converting, or the existing
# passwords of the client users would be invalidated
LEGACY_PASSWORD_SALT = "test"
FIELDS = {**ServerSettings.model_fields, **ClientSettings.model_fields}


def random_secret():
    return secrets.token_urlsafe(32)


def env_value(value):
    """Format a Python value for a .env file (dicts and lists as JSON)"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        # JSON over several lines (between single quotes) if not empty, for readability
        value = json.dumps(value, indent=4) if value else json.dumps(value)
        return f"'{value}'" if "'" not in value else json.dumps(value)
    value = str(value)
    if re.search(r"[\s#'\"\\$]", value):
        return json.dumps(value)  # double quotes, with escapes
    return value


def from_template(template=TEMPLATE):
    """Content of a template, with random values for the empty secrets"""
    lines = []
    with open(template) as f:
        for line in f.read().splitlines():
            m = re.match(r"^OPUS_(\w+)=$", line)
            if m and m.group(1) in RANDOM_SECRETS:
                line += random_secret()
            lines.append(line)
    return "\n".join(lines) + "\n"


def from_settings_local(path):
    """Values of a settings_local.py file as OPUS_* variables"""
    spec = importlib.util.spec_from_file_location("settings_local", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values = {k: v for k, v in vars(module).items() if k.isupper()}
    lines = [
        f"# OPUS settings converted from {os.path.abspath(path)}",
        "# Keep this file private: no git tracking, no public read access",
        "",
    ]
    ignored = []
    for name, value in values.items():
        if name not in FIELDS:
            ignored.append(name)
        elif callable(value):
            ignored.append(f"{name} (function, set it as an import string 'module:function')")
        else:
            lines.append(f"OPUS_{name}={env_value(value)}")
    lines += ["", "# New required secrets"]
    if "SECRET_KEY" not in values:
        lines.append(f"OPUS_SECRET_KEY={random_secret()}")
    if "SECURITY_PASSWORD_SALT" not in values:
        lines += [
            "# Salt used until now: changing it invalidates all the existing passwords",
            f"OPUS_SECURITY_PASSWORD_SALT={LEGACY_PASSWORD_SALT}",
        ]
    if ignored:
        lines += ["", "# Ignored from settings_local.py (not settings):"]
        lines += [f"#   {name}" for name in ignored]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", help="settings_local.py file to convert")
    parser.add_argument("--template", default=TEMPLATE, help="template file (default: .env.dist)")
    args = parser.parse_args()
    sys.stdout.write(from_settings_local(args.source) if args.source else from_template(args.template))
