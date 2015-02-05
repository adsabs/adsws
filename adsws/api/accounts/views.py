# from flask.ext.jwt import jwt_required
# from flask import Blueprint

import datetime

from werkzeug.security import gen_salt

from adsws.modules.oauth2server.provider import oauth2
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken

from adsws.core import db, user_manipulator

from flask.ext.ratelimiter import ratelimit
from flask.ext.login import current_user, login_user
from flask.ext.restful import Resource
from flask import Blueprint, current_app, session, abort, request

def scope_func():
  if hasattr(request,'oauth') and request.oauth.client:
    return request.oauth.client.client_id
  return request.remote_addr

class UserAuthView(Resource):
  decorators = [ratelimit(10,120,scope_func=scope_func)]
  def post(self):
    #login pattern, return oauth token
    try:
      username = request.json.get('username')
      password = request.json.get('password')
    except:
      return {'error':'malformed request'}, 400

  def get(self):
    #view pattern, return profile/user attributes
    pass

class UserRegistrationView(Resource):
  decorators = [ratelimit(5,600,scope_func=scope_func)]
  def post(self):
    pass
