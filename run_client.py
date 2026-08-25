from uws_client.uws_client import app, CONFIG_FILE

print("\nImportant: Check that EDITABLE_CONFIG is well defined in: {} (Some variables may be overwritten by this EDITABLE_CONFIG)\n".format(CONFIG_FILE))

app.run(host='localhost', port=8080, debug=True)
