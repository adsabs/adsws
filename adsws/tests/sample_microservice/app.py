from flask import Flask
from views import Resources, GET, POST, GETPOST, SCOPED, LOW_RATE_LIMIT, \
    PUT, EchoHeaders, DELETE, _410Response, RETAIN_HEADERS
from flask_restful import Api


def create_app():
    app = Flask(__name__, static_folder=None)

    app.url_map.strict_slashes = False
    app.config.from_pyfile('config.py')
    try:
        app.config.from_pyfile('local_config.py')
    except IOError:
        pass

    # hack for tests: blueprint needs to be destroyed
    # between tests, otherwise _registered_once=False
    # will cause app.register_blueprint to fail
    # reload(views)
    api = Api(app)

    api.add_resource(Resources, '/resources')
    api.add_resource(EchoHeaders, '/ECHO_HEADERS')
    api.add_resource(GET, '/GET')
    api.add_resource(POST, '/POST')
    api.add_resource(PUT, '/PUT')
    api.add_resource(DELETE, '/DELETE')
    api.add_resource(GETPOST, '/GETPOST')
    api.add_resource(SCOPED, '/SCOPED')
    api.add_resource(LOW_RATE_LIMIT, '/LOW_RATE_LIMIT')
    api.add_resource(_410Response, '/410')
    api.add_resource(RETAIN_HEADERS, '/RETAIN_HEADERS')

    return app


def run():
    app = create_app()
    app.run(host='127.0.0.1', port=5005, processes=5, debug=False)

if __name__ == "__main__":
    run()
