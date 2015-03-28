from .. import factory

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

  return app