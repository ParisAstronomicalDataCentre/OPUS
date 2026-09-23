#!/usr/bin/env python

from uws_client.uws_client import app, settings

CONFIG_FILE = settings.CONFIG_FILE

print(
    f"\nImportant: Check that EDITABLE_CONFIG is well defined in: {CONFIG_FILE} (Some variables may be overwritten by this EDITABLE_CONFIG)\n"
)

app.run(host="localhost", port=8080, debug=True)
