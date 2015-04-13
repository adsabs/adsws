# from flask.ext.jwt import jwt_required
# from flask import Blueprint

import datetime
import requests
from werkzeug.security import gen_salt

from adsws.modules.oauth2server.models import OAuthClient, OAuthToken
from adsws.modules.oauth2server.provider import oauth2

from adsws.core import db, user_manipulator

from flask.ext.ratelimiter import ratelimit
from flask.ext.login import current_user, login_user, logout_user
from flask.ext.restful import Resource, abort
from flask.ext.wtf.csrf import generate_csrf
from flask import Blueprint, current_app, session, abort, request
from .utils import (
  scope_func, validate_email, validate_password, 
  verify_recaptcha, get_post_data, send_email)
from .exceptions import ValidationError
from .emails import (PASSWORD_RESET_EMAIL, 
                    VERIFICATION_EMAIL,)

class StatusView(Resource):
  def get(self):
    return {'app':current_app.name,'status': 'online'}, 200

class ProtectedView(Resource):
  '''This view is oauth2-authentication protected'''
  decorators = [oauth2.require_oauth()]
  def get(self):
    return {'app':current_app.name,'oauth':request.oauth.user.email}

class DeleteAccountView(Resource):
  def post(self):
    '''
    Delete the current user's account
    use POST instead of GET to be validated by csrf protection
    '''
    if not current_user.is_authenticated() or current_user.email == current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)

    u = user_manipulator.first(email=current_user.email)
    logout_user()
    user_manipulator.delete(u)
    return {"message":"success"}, 200

class ForgotPasswordView(Resource):
  def get(self,token):
    '''
    Decode a token into an email, if the signature is validated.
    Log the user in without a password so that the PUT method works
    '''
    try:
      email = current_app.ts.loads(token, max_age=600, salt=PASSWORD_RESET_EMAIL.salt)
    except:
      return {"error":"unknown verification token"}, 404

    u = user_manipulator.first(email=email)
    if u is None:
      current_app.logger.warning("[GET] Reset password validated link, but no user exists for {email}".format(email=email))
      abort(500)
    return {"email":email}, 200
  
  def post(self,token):
    '''
    Send the password reset email to the specified email address (recaptcha protected)
    '''
    if token==current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(403)
    try:
      data = get_post_data(request)
      reset_url = data['reset_url']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400
    if not verify_recaptcha(request):
      return {'error': 'captcha was not verified'}, 403
    
    u = user_manipulator.first(email=token)
    if u is None:
      return {'error':'no such user exists'}, 404

    if not u.confirmed_at:
      return {'error':'this user was never verified. It should be deleted within a day'}, 403
    send_email(token,reset_url,PASSWORD_RESET_EMAIL, token)
    return {"message":"success"}
  
  def put(self,token):
    '''
    Check if the current user has the right email, and, if so, change the password
    '''
    try:
      email = current_app.ts.loads(token, max_age=600, salt=PASSWORD_RESET_EMAIL.salt)
    except:
      current_app.logger.warning("PUT on reset-password with invalid token. This indicates a brute-force attack!")
      return {"error":"unknown verification token"}, 404

    try:
      data = get_post_data(request)
      new_password1 = data['password1']
      new_password2 = data['password2']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400

    if new_password1 != new_password2:
      return {'error':'passwords do not match'}, 400
    try:
      validate_password(new_password1)
    except ValidationError, e:
      return {'error':'validation error'}, 400

    u = user_manipulator.first(email=email)
    if u is None:
      current_app.logger.warning("[PUT] Reset password validated link, but no user exists for {email}".format(email=email))
      abort(500)
    user_manipulator.update(u,password=new_password1)
    logout_user()
    login_user(u,force=True)
    return {"message":"success"}, 200

class ChangePasswordView(Resource):
  def post(self):
    if not current_user.is_authenticated() or current_user.email == current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)

    try:
      data = get_post_data(request)
      old_password = data['old_password']
      new_password1 = data['new_password1']
      new_password2 = data['new_password2']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400

    if not current_user.validate_password(old_password):
      return {'error':'please verify your current password'},401

    if new_password1 != new_password2:
      return {'error':'passwords do not match'}, 400
    try:
      validate_password(new_password1)
    except ValidationError, e:
      return {'error':'validation error'}, 400

    u = user_manipulator.first(email=current_user.email)
    user_manipulator.update(u,password=new_password1)
    return {'message':'success'}

class PersonalTokenView(Resource):
  decorators = [ratelimit(20,600,scope_func=scope_func)]
  def get(self):
    '''GET to this endpoint returns the ADS API client token, which
    is effectively a personal access token'''
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
    '''POST to this endpoint generates a new API key'''
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
      _default_scopes=' '.join(current_app.config['USER_API_DEFAULT_SCOPES']),
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
        _scopes=' '.join(current_app.config['USER_API_DEFAULT_SCOPES']),
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

class ChangeEmailView(Resource):
  decorators = [ratelimit(1000,600,scope_func=scope_func)]  
  def post(self):
    '''
    POST desired email and password to change email, if that email isn't already registerd

    This will DEACTIVATE the current user, meaning that the user will have to visit a new
    confirm email link to reactive their account
    '''

    if not current_user.is_authenticated() or current_user.email==current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)
    try:
      data = get_post_data(request)
      email = data['email']
      password = data['password']
      verify_url = data['verify_url']
    except (AttributeError, KeyError):
      return {'error':'malformed request'}, 400

    u = user_manipulator.first(email=current_user.email)
    if not u.validate_password(password):
      abort(401)
        
    if user_manipulator.first(email=email) is not None:
      return {"error":"{email} has already been registered".format(email=email)}, 403
    send_email(email,verify_url,VERIFICATION_EMAIL, email)
    user_manipulator.update(u, email=email, confirmed_at=None)
    logout_user()
    return {"message":"success"},200

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
    if u is None or not u.validate_password(password):
      abort(401)
    if u.confirmed_at is None:
      return {"error":"account has not been verified"}, 403

    if current_user.is_authenticated(): #Logout of previous user (may have been bumblebee)
      logout_user()
    login_user(u,force=True) #Login to real user
    return {"message":"success"}, 200

  def get(self):
    #view pattern, return profile/user attributes
    if not current_user.is_authenticated() or current_user.email==current_app.config['BOOTSTRAP_USER_EMAIL']:
      abort(401)
    return {"user":current_user.email}

class VerifyEmailView(Resource):
  decorators = [ratelimit(20,600,scope_func=scope_func)]
  def get(self,token):
    try:
      email = current_app.ts.loads(token, max_age=86400,salt=VERIFICATION_EMAIL.salt)
    except:
      return {"error":"unknown verification token"}, 404

    u = user_manipulator.first(email=email)
    if u is None:
      return {"error":"no user associated with that verification token"}, 404
    if u.confirmed_at is not None:
      return {"error": "this user and email has already been validated"}, 400

    user_manipulator.update(u,confirmed_at=datetime.datetime.now())
    login_user(u, remember=False, force=True)
    return {"message":"success","email":email}

class UserRegistrationView(Resource):
  decorators = [ratelimit(50,600,scope_func=scope_func)]
  def post(self):
    try:
      data = get_post_data(request)
      email = data['email']
      password = data['password1']
      repeated = data['password2']
      verify_url = data['verify_url']
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
      return {'error':'validation error'}, 400

    if user_manipulator.first(email=email) is not None:
      return {'error':'an account is already registered with that email'}, 409
    send_email(email,verify_url,VERIFICATION_EMAIL, email)
    u = user_manipulator.create(
      email=email, 
      password=password
    )
    return {"message":"success"}, 200

class Bootstrap(Resource):
  decorators = [ratelimit(400,86400,scope_func=scope_func)]

  def get(self):
    """Returns the datastruct necessary for Bumblebee bootstrap."""

    #Non-authenticated = login as bumblebee user
    if not current_user.is_authenticated() or current_user.email == current_app.config['BOOTSTRAP_USER_EMAIL']:
      token = bootstrap_bumblebee()
    else:
      token = bootstrap_user()

    return {
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'username': current_user.email,
            'expire_in': token.expires.isoformat() if isinstance(token.expires,datetime.datetime) else token.expires,
            'token_type': 'Bearer',
            'scopes': token.scopes,
            'csrf': generate_csrf(),
           }

def bootstrap_bumblebee():
  salt_length = current_app.config.get('OAUTH2_CLIENT_ID_SALT_LEN', 40)
  scopes = ' '.join(current_app.config['BOOTSTRAP_SCOPES'])
  user_email = current_app.config['BOOTSTRAP_USER_EMAIL']
  expires = current_app.config.get('BOOTSTRAP_TOKEN_EXPIRES', 3600*24)
  u = user_manipulator.first(email=user_email)
  if u is None:
    current_app.logger.error("No user exists with email [%s]" % user_email)
    abort(500)
  login_user(u, remember=False, force=True)
  client, token = None, None

  #See if the session has a memory of the client
  if '_oauth_client' in session:
    client = OAuthClient.query.filter_by(
      client_id=session['_oauth_client'],
      user_id=current_user.get_id(),
      name=u'BB client',
    ).first()
          
  if client is None:
    client = OAuthClient(
      user_id=current_user.get_id(),
      name=u'BB client',
      description=u'BB client',
      is_confidential=False,
      is_internal=True,
      _default_scopes=scopes,
    )
    client.gen_salt()
    
    db.session.add(client)
    db.session.commit()
    session['_oauth_client'] = client.client_id

  token = OAuthToken.query.filter_by(
    client_id=client.client_id, 
    user_id=current_user.get_id(),
    is_personal=False,
    is_internal=True,
  ).filter(OAuthToken.expires > datetime.datetime.now()).first()

  if token is None:
    if isinstance(expires,int):
      expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires)
    token = OAuthToken(
      client_id=client.client_id,
      user_id=current_user.get_id(),
      access_token=gen_salt(salt_length),
      refresh_token=gen_salt(salt_length),
      expires=expires,
      _scopes=scopes,
      is_personal=False,
      is_internal=True,
    )

    db.session.add(token)
    try:
      db.session.commit()
    except:
      db.session.rollback()
      abort(503)
  return token

def bootstrap_user():
  client = OAuthClient.query.filter_by(
      user_id=current_user.get_id(),
      name=u'BB client',
    ).first()
  if client is None:
    scopes = ' '.join(current_app.config['USER_DEFAULT_SCOPES'])
    salt_length = current_app.config.get('OAUTH2_CLIENT_ID_SALT_LEN', 40)
    client = OAuthClient(
      user_id=current_user.get_id(),
      name=u'BB client',
      description=u'BB client',
      is_confidential=True,
      is_internal=True,
      _default_scopes=scopes,
    )
    client.gen_salt()
    db.session.add(client)
    try:
      db.session.commit()
    except:
      db.session.rollback()
      abort(503)

    token = OAuthToken(
      client_id=client.client_id,
      user_id=current_user.get_id(),
      access_token=gen_salt(salt_length),
      refresh_token=gen_salt(salt_length),
      expires= datetime.datetime(2500,1,1),
      _scopes=scopes,
      is_personal=False,
      is_internal=True,
    )
    db.session.add(token)
    try:
      db.session.commit()
    except:
      db.session.rollback()
      abort(503)
    current_app.logger.info("Created BB client for {email}".format(email=current_user.email))
  else:
    token = OAuthToken.query.filter_by(
      client_id=client.client_id, 
      user_id=current_user.get_id(),
    ).first()

  session['_oauth_client'] = client.client_id
  return token

