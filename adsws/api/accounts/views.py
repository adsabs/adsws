# from flask.ext.jwt import jwt_required
# from flask import Blueprint

import datetime
import requests
from werkzeug.security import gen_salt

from adsws.modules.oauth2server.provider import oauth2
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken

from adsws.core import db, user_manipulator

from flask.ext.ratelimiter import ratelimit
from flask.ext.login import current_user, login_user, logout_user
from flask.ext.security.utils import verify_and_update_password
from flask.ext.restful import Resource, abort
from flask import Blueprint, current_app, session, abort, request
from utils import scope_func, validate_email, validate_password, verify_recaptcha, send_verification_email


class LogoutView(Resource):
  def get(self):
    logout_user()
    return {"message":"success"}, 200

class UserAuthView(Resource):
  decorators = [ratelimit(100,120,scope_func=scope_func)]
  def post(self):
    try:
      if request.headers.get('content-type','application/json')=='application/json':
        data = request.json
      else:
        data = request.data
      username = data['username']
      password = data['password']
    except (AttributeError, KeyError):
        return {'error':'malformed request'}, 400

    u = user_manipulator.first(email=username)
    if u is None or not verify_and_update_password(password,u):
      abort(401)
    if u.confirmed_at is None:
      return {"message":"account has not been verified"}, 403

    if current_user.is_authenticated(): #Logout of previous user (may have been bumblebee)
      logout_user()
    login_user(u) #Login to real user
    return {"message":"success"}, 200

  def get(self):
    #view pattern, return profile/user attributes
    if not current_user.is_authenticated():
      abort(401)
    return {"user":current_user.email}

class VerifyEmailView(Resource):
  decorators = [ratelimit(50,600,scope_func=scope_func)]
  def get(self,token):
    try:
      email = current_app.ts.loads(token, max_age=86400)
    except:
      return {"error":"unknown verification token"}, 404

    u = user_manipulator.first(email=email)
    if u is None:
      return {"error":"no user associated with that verification token"}, 404
    if u.confirmed_at is not None:
      return {"error": "this user and email has already been validated"}, 400

    user_manipulator.update(u,confirmed_at=datetime.datetime.now())
    return {"message":"success","email":email}



class UserRegistrationView(Resource):
  decorators = [ratelimit(50,600,scope_func=scope_func)]
  def post(self):
    try:
      if request.headers.get('content-type','application/json')=='application/json':
        data = request.json
      else:
        data = request.data
      email = data['email']
      password = data['password1']
      repeated = data['password2']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400
    if not verify_recaptcha(request):
      return {'error': 'captcha was not verified'}, 403
    if password!=repeated:
      return {'error': 'passwords do not match'}, 400
    try:
      validate_email(email)
      validate_password(password)
    except ValidationError, e:
      return {'error':e}, 400

    if user_manipulator.first(email=email) is not None:
      return {'error':'an account is already registered with that email'}, 409

    send_verification_email(email)
    u = user_manipulator.create(
      email=email, 
      password=password
      )
    return {"message":"success"}, 200



