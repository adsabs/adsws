import datetime

from werkzeug.security import gen_salt

from adsws.modules.oauth2server.provider import oauth2
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken

from adsws.core import db, user_manipulator


from flask.ext.login import current_user, login_user
from flask.ext.restful import Resource
from flask import Blueprint, current_app, session, abort

class StatusView(Resource):
  '''Returns the status of this app'''
  def get(self):
    return {'app':current_app.name,'status': 'online'}, 200

class Bootstrap(Resource):
  def get(self):
    
    """Returns the datastruct necessary for Bumblebee bootstrap."""
    scopes = ' '.join(current_app.config.get('BOOTSTRAP_SCOPES',['ads:default']))
    user_email = current_app.config.get('BOOTSTRAP_USER_EMAIL','anon@ads.org')
    salt_length = current_app.config.get('OAUTH2_CLIENT_ID_SALT_LEN', 40)
    expires = current_app.config.get('BOOTSTRAP_TOKEN_EXPIRES', 3600*24)

    if not current_user.is_authenticated():
      u = user_manipulator.first(email=user_email)
      if u is None:
        current_app.logger.error("No user exists with email [%s]" % user_email)
        abort(500)
      login_user(u, remember=False, force=True)
    
    client = None
    if '_oauth_client' in session:
      client = OAuthClient.query.filter_by(
        client_id=session['_oauth_client'],
        user_id=current_user.get_id(),
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
      expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(expires))
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

    return {
            'access_token': token.access_token,
            #'refresh_token': token.refresh_token,
            #'username': current_user.email,
            'expire_in': token.expires.isoformat(),
            'token_type': 'Bearer',
            'scopes': token.scopes,
            }