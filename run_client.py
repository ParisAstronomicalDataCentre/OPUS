#!/usr/bin/env python

from uws_client.uws_client import CONFIG_FILE, app

print(
    f"\nImportant: Check that EDITABLE_CONFIG is well defined in: {CONFIG_FILE} (Some variables may be overwritten by this EDITABLE_CONFIG)\n"
)

app.run(host="localhost", port=8080, debug=True)
