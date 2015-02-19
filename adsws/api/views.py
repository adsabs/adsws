import datetime

from adsws.modules.oauth2server.provider import oauth2
from flask.ext.restful import Resource
from flask import current_app, request

def scope_func():
  #We could do something more complex in the future
  return request.remote_addr

class ProtectedView(Resource):
  '''This view is oauth2-authentication protected'''
  decorators = [oauth2.require_oauth()]
  def get(self):
    return {'app':current_app.name,'oauth':request.oauth.user.email}

class StatusView(Resource):
  '''Returns the status of this app'''
  def get(self):
    return {'app':current_app.name,'status': 'online'}, 200