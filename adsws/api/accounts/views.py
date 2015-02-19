# from flask.ext.jwt import jwt_required
# from flask import Blueprint

import datetime
import requests
from werkzeug.security import gen_salt

from adsws.modules.oauth2server.models import OAuthClient, OAuthToken

from adsws.core import db, user_manipulator

from flask.ext.ratelimiter import ratelimit
from flask.ext.login import current_user, login_user, logout_user
from flask.ext.security.utils import verify_and_update_password
from flask.ext.restful import Resource, abort
from flask import Blueprint, current_app, session, abort, request
from utils import (
  scope_func, validate_email, validate_password, 
  verify_recaptcha, send_verification_email, get_post_data)

class ChangePasswordView(Resource):
  def post(self):
    try:
      data = get_post_data(request)
      old_password = data['old_password']
      new_password1 = data['new_password1']
      new_password2 = data['new_password2']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400

    if not current_user.is_authenticated() or current_user.email == current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)

    if not current_user.validate_password(old_password):
      return {'error':'please verify your current password'},401

    if new_password1 != new_password2:
      return {'error':'passwords do not match'}, 400

    u = user_manipulator.first(email=current_user.email)
    user_manipulator.update(u,password=new_password1)
    return {'message':'success'}

class PersonalTokenView(Resource):
  decorators = [ratelimit(50,86400,scope_func=scope_func)]
  def get(self):
    if not current_user.is_authenticated() or current_user.email==current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)
    client = OAuthClient.query.filter_by(
      user_id=current_user.get_id(),
      name=u'ADS API client',
    ).first()
    if not client:
      return {'message':'no ADS API client found'}, 200

    token = OAuthToken.query.filter_by(
      client_id=client.client_id, 
      user_id=current_user.get_id(),
    ).first()

    if not token:
      current_app.logger.error('no ADS API client token found for {email}. This should not happen!'.format(email=current_user.email))
      return {'message':'no ADS API client token found. This should not happen!'}, 500

    return {
          'access_token': token.access_token,
          'refresh_token': token.refresh_token,
          'username': current_user.email,
          'expire_in': token.expires.isoformat() if isinstance(token.expires,datetime.datetime) else token.expires,
          'token_type': 'Bearer',
          'scopes': token.scopes,
         }

  def post(self):
    '''POSTING to this endpoint generates a new API key'''
    if not current_user.is_authenticated() or current_user.email==current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)

    client = OAuthClient.query.filter_by(
      user_id=current_user.get_id(),
      name=u'ADS API client',
    ).first()

    if client is None:
      client = OAuthClient(
      user_id=current_user.get_id(),
      name=u'ADS API client',
      description=u'ADS API client',
      is_confidential=False,
      is_internal=True,
      _default_scopes=' '.join(current_app.config['USER_DEFAULT_SCOPES']),
    )
    client.gen_salt()
    
    db.session.add(client)
    try:
      db.session.commit()
    except:
      abort(503)
    current_app.logger.info("Created ADS API client for {email}".format(email=current_user.email))
    token = OAuthToken.query.filter_by(
      client_id=client.client_id, 
      user_id=current_user.get_id(),
    ).first()

    if token is None:
      token = OAuthToken(
        client_id=client.client_id,
        user_id=current_user.get_id(),
        access_token=gen_salt(40),
        refresh_token=gen_salt(40),
        expires=datetime.datetime(2500,1,1),
        _scopes=' '.join(current_app.config['USER_DEFAULT_SCOPES']),
        is_personal=False,
      )
      db.session.add(token)
      try:
        db.session.commit()
      except:
        db.session.rollback()
        abort(503)
    else:
      token.access_token = gen_salt(40)

    db.session.add(token)
    try:
      db.session.commit()
    except:
      db.session.rollback()
      abort(503)  
    current_app.logger.info("Updated ADS API token for {email}".format(email=current_user.email))
    return {
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'username': current_user.email,
            'expire_in': token.expires.isoformat() if isinstance(token.expires,datetime.datetime) else token.expires,
            'token_type': 'Bearer',
            'scopes': token.scopes,
           }




class LogoutView(Resource):
  def get(self):
    logout_user()
    return {"message":"success"}, 200

class UserAuthView(Resource):
  decorators = [ratelimit(50,120,scope_func=scope_func)]
  def post(self):
    try:
      data = get_post_data(request)
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
    if not current_user.is_authenticated() or current_user.email==current_app.config['BOOTSTRAP_USER_EMAIL']:
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
      data = get_post_data(request)
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