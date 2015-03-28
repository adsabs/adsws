from .. import factory

from flask import jsonify
from flask.ext.ratelimiter import RateLimiter
from flask.ext.restful import Api
from .views import (GlobalResourcesView, StatusView)


def create_app(resources={},**kwargs_config):
  app = factory.create_app(app_name=__name__.replace('.app',''), **kwargs_config)

  app.config['resources'] = resources
  api = Api(app)
  api.unauthorized = lambda noop: noop #Overwrite WWW-Authenticate challenge on 401

  ratelimiter = RateLimiter(app=app)

  api.add_resource(StatusView,'/',endpoint="root_statusview")  
  api.add_resource(StatusView,'/status')
  api.add_resource(GlobalResourcesView,'/resources')

  # Register custom error handlers
  if not app.config.get('DEBUG'):
    app.errorhandler(404)(on_404)
    app.errorhandler(401)(on_401)
  return app

def on_404(e):
  return jsonify(dict(error='Not found')), 404

def on_401(e):
  return jsonify(dict(error='Unauthorized')), 401
