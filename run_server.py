from uws_server.uws_server import app, run

run(app, host="localhost", port=8082, debug=False, reloader=True)
