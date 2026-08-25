from uws_server.uws_server import run, app

run(app, host='localhost', port=8082, debug=False, reloader=True)
