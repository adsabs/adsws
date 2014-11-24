from flask import Blueprint, request, current_app, jsonify
from flask.ext.restful import Resource
from urlparse import urljoin
import requests
import json

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

  #Having a dispatched based on request.method solves
  #being able to set up ProxyViews on the same resource for different routes,
  #however it limits the ability to scope a resouce on a per-method basis
  def _dispatcher(self,**kwargs):
    path = request.full_path.replace(self.deploy_path,'',1)
    path = path[1:] if path.startswith('/') else path
    ep = urljoin(self.service_uri,path)
    return self.__getattribute__(request.method.lower())(ep,request)

  def get(self,ep,request,**kwargs):
    r = requests.get(ep,headers=request.headers)
    return jsonify(r.json())

  def post(self,ep,request,**kwargs):
    if not isinstance(request.data,basestring):
      request.data = json.dumps(request.data)
    r = requests.post(ep,data=request.data,headers=request.headers)
    resp = r.json()
    if isinstance(resp, basestring): #Just necessary for httpretty in unittests
      resp = json.loads(resp)
    return jsonify(resp)
