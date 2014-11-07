from flask import Blueprint, request, current_app, jsonify
from flask.ext.restful import Resource
import requests

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

  def get(self,*args):
    r = requests.get(self.endpoint)
    return jsonify(r.json())

    #return "generic view for <h1>%s</h1>" % self.endpoint