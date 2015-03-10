from flask import current_app, Blueprint
from flask.ext.restful import Resource
import time
import inspect
import sys
import config
from client import Client
from stubdata import Stubdata

if not hasattr(config,'CLIENT'):
  config.CLIENT = None
client = Client(config.CLIENT)

#This resource must be available for every adsabs webservice.
class Resources(Resource):
  '''Overview of available resources'''
  scopes = []
  rate_limit = [1000,60*60*24]
  def get(self):
    func_list = {}
    clsmembers = [i[1] for i in inspect.getmembers(sys.modules[__name__], inspect.isclass)]
    for rule in current_app.url_map.iter_rules():
      f = current_app.view_functions[rule.endpoint]
      #If we load this webservice as a module, we can't guarantee that current_app only has these views
      if not hasattr(f,'view_class') or f.view_class not in clsmembers:
        continue
      methods = f.view_class.methods
      scopes = f.view_class.scopes
      rate_limit = f.view_class.rate_limit
      description = f.view_class.__doc__
      func_list[rule.rule] = {'methods':methods,'scopes': scopes,'description': description,'rate_limit':rate_limit}
    return func_list, 200

class GET(Resource):
  '''desc for GET'''
  scopes = []
  rate_limit = [1000,60*60*24]
  def get(self):
    return Stubdata.GET

class POST(Resource):
  '''desc for POST'''
  scopes = []
  rate_limit = [1000,60*60*24]
  def post(self):
    return Stubdata.POST

class GETPOST(Resource):
  '''desc for GETPOST'''
  scopes = []
  rate_limit = [1000,60*60*24]
  def get(self):
    return Stubdata.GETPOST['GET']
  def post(self):
    return Stubdata.GETPOST['POST']

class SCOPED(Resource):
  '''desc for SCOPES'''
  scopes = ['this-scope-shouldnt-ever-exist']
  rate_limit = [1000,60*60*24]
  def get(self):
    return {'msg': 'This response should not be possible to recieve!'}

class LOW_RATE_LIMIT(Resource):
  '''desc for LOW_RATE_LIMIT'''
  scopes = []
  rate_limit = [3,10]
  def get(self):
    return {'status':'OK'}
