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
import requests

def scope_func():
  if hasattr(request,'oauth') and request.oauth.client:
    return request.oauth.client.client_id
  return request.remote_addr

def verify_recaptcha(request):
  payload = {
    'secret': current_app.config['GOOGLE_RECAPTCHA_PRIVATE_KEY'],
    'remoteip': request.remote_addr,
    'response': request.json['g-recaptcha-response'],
  }
  ep = current_app.config['GOOGLE_RECAPTCHA_ENDPOINT']
  r = requests.get(ep,params=payload)
  r.raise_for_status()
  return True if r.json()['success'] == True else False

class UserAuthView(Resource):
  decorators = [ratelimit(10,120,scope_func=scope_func)]
  def post(self):
    #login pattern, return oauth token
    try:
      username = request.json['username']
      password = request.json['password']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400
    return {"msg":"OK"}

  def get(self):
    #view pattern, return profile/user attributes
    raise NotImplementedError

class UserRegistrationView(Resource):
  decorators = [ratelimit(5,600,scope_func=scope_func)]
  def post(self):
    raise NotImplementedError
