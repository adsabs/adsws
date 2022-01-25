from ..core import AdsWSError, AdsWSFormError, JSONEncoder
from .. import factory

from flask_restful import Api
from flask_cors import CORS
from flask import jsonify

from .views import StatusView, ProtectedView, UserResolver
from .discoverer import discover


def create_app(**kwargs_config):
    app = factory.create_app(
        app_name=__name__.replace('.app', ''),
        **kwargs_config
    )

    api = Api(app)

    # Overwrite WWW-Authenticate challenge on 401
    api.unauthorized = lambda noop: noop

    CORS(
        app,
        origins=app.config.get('CORS_DOMAINS'),
        allow_headers=app.config.get('CORS_HEADERS'),
        methods=app.config.get('CORS_METHODS')
    )
    
    # here is where we collect data for ratelimiting    
    app.extensions['symbolic_ratelimits'] = {}

    app.json_encoder = JSONEncoder
    api.add_resource(StatusView, '/status')
    api.add_resource(ProtectedView, '/protected')
    api.add_resource(UserResolver, '/user/<string:identifier>')
    discover(app)  # Incorporate local and remote applications into this one

    # Register custom error handlers
    if not app.config.get('DEBUG'):
        app.errorhandler(AdsWSError)(on_adsws_error)
        app.errorhandler(AdsWSFormError)(on_adsws_form_error)
    
    
    return app

def on_adsws_error(e):
    return jsonify(dict(error=e.msg)), 400

def on_adsws_form_error(e):
    return jsonify(dict(errors=e.errors)), 400
