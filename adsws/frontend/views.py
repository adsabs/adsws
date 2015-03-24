from flask import current_app

from flask.ext.restful import Resource
from flask.ext.ratelimiter import ratelimit
from .utils import scope_func

class StatusView(Resource):
  decorators = [ratelimit(1000,24*60*60,scope_func=scope_func)]
  def get(self):
    return {'app':current_app.name,'status': 'online'}, 200

class GlobalResourcesView(Resource):
  decorators = [ratelimit(1000,24*60*60,scope_func=scope_func)]
  def get(self):
    return current_app.config['resources']
