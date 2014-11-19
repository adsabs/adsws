from flask import Blueprint, request, current_app, jsonify
from flask.ext.restful import Resource
from urlparse import urljoin
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

class ProxyView(Resource):
  '''Proxies a request to a webservice'''

  def __init__(self,endpoint, service_uri, deploy_path):
    self.endpoint = endpoint
    self.service_uri = service_uri
    self.deploy_path = deploy_path

  def get(self,**kwargs):
    path = request.full_path.replace(self.deploy_path,'',1)
    path = path[1:] if path.startswith('/') else path
    ep = urljoin(self.service_uri,path)
    r = requests.get(ep)
    return jsonify(r.json())

  def post(self,**kwargs):
    path = request.full_path.replace(self.deploy_path,'',1)
    path = path[1:] if path.startswith('/') else path
    ep = urljoin(self.service_uri,path)
    r = requests.post(ep,data=request.form)
    return jsonify(r.json())