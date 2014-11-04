from flask import Blueprint, request, current_app
from flask.ext.restful import Resource

blueprint = Blueprint(
  'discoverer',
  __name__,
  static_folder=None,
)

class StatusView(Resource):
  '''Returns the status of this app'''
  def get(self):
    return {'app':current_app.name,'status': 'online'}, 200

class ProxyView:
  def __init__(self,endpoint):
    self.endpoint = endpoint

  def get(self):
    return "generic view for <h1>%s</h1>" % self.endpoint