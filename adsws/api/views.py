import datetime

from werkzeug.security import gen_salt
import datetime

from adsws.modules.oauth2server.provider import oauth2
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken

from adsws.core import db, user_manipulator

from flask.ext.ratelimiter import ratelimit
from flask.ext.login import current_user, login_user
from flask.ext.restful import Resource
from flask.ext.wtf.csrf import generate_csrf
from flask import Blueprint, current_app, session, abort, request

def scope_func():
  #We could do something more complex in the future
  return request.remote_addr

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
  ).first()

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

class ProtectedView(Resource):
  '''This view is oauth2-authentication protected'''
  decorators = [oauth2.require_oauth()]
  def get(self):
    return {'app':current_app.name,'oauth':request.oauth.user.email}

class StatusView(Resource):
  '''Returns the status of this app'''
  def get(self):
    return {'app':current_app.name,'status': 'online'}, 200

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