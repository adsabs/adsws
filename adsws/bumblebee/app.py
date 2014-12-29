from ..core import AdsWSError, AdsWSFormError, JSONEncoder
from .. import factory

from flask.ext.ratelimiter import RateLimiter
from flask.ext.restful import Api
from flask.ext.cors import CORS
from flask.ext.login import LoginManager
from flask import jsonify

from views import StatusView,Bootstrap

def create_app(**kwargs_config):
  
  app = factory.create_app(app_name=__name__.replace('.app',''), **kwargs_config)
  api = Api(app)
  ratelimiter = RateLimiter(app=app)
  cors = CORS(app,origins=app.config.get('CORS_DOMAINS'), headers=app.config.get('CORS_HEADERS'))

  app.json_encoder = JSONEncoder
  api.add_resource(StatusView,'/status')
  api.add_resource(Bootstrap,'/bootstrap')

  # Register custom error handlers
  if not app.config.get('DEBUG'):
    app.errorhandler(AdsWSError)(on_adsws_error)
    app.errorhandler(AdsWSFormError)(on_adsws_form_error)
    app.errorhandler(404)(on_404)
    app.errorhandler(401)(on_401)

  return app


def on_adsws_error(e):
  return jsonify(dict(error=e.msg)), 400

def on_adsws_form_error(e):
  return jsonify(dict(errors=e.errors)), 400

def on_404(e):
  return jsonify(dict(error='Not found')), 404

def on_401(e):
  return jsonify(dict(error='Unauthorized')), 401
