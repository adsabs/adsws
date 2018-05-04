import argparse
import json
import sys,os
PROJECT_HOME=os.path.join(os.path.dirname(__file__),'..')
sys.path.append(PROJECT_HOME)
from adsws.core import db, user_manipulator
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken
from adsws.core.users.models import User
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from werkzeug.security import gen_salt
from adsws.factory import create_app
from flask import current_app
import datetime

class DatabaseIntegrityError(Exception):
  def __init__(self,value="Multiple entries found for what should have been a unique query. This suggests that the database is not in a correct state!"):
    self.value = value
  def __str__(self):
    return repr(self.value)

def add_arguments(parser):
  parser.add_argument(
    '--user-email',
    required=True,
    dest='user_email',
    help='The user identifier (email) associated with this token'
    )

  parser.add_argument(
    '--description',
    required=False,
    default = '',
    dest='description',
    help='A description for this client'
    )
  parser.add_argument(
    '--name',
    required=True,
    dest='name',
    help='Name of the oauth client'
    )

  parser.add_argument(
    '--create-user',
    required=False,
    default=False,
    action='store_true',
    dest='create_user',
    help='Create the user if it doesn\'t exist'
    )

  parser.add_argument(
    '--scopes',
    required=True,
    nargs='*',
    dest='scopes',
    help='Space separated list of scopes'
    )

  parser.add_argument(
    '--personal',
    default=False,
    action='store_true',
    dest='is_personal',
    help='Set the token type'
    )


def get_token():
  parser = argparse.ArgumentParser()
  add_arguments(parser)
  args = parser.parse_args()
  app = create_app('manual_client_registration',
    EXTENSIONS = ['adsws.ext.sqlalchemy',
                  'adsws.ext.security',],
    PACKAGES=['adsws.modules.oauth2server',])

  with app.app_context() as context:
    try:
      u = db.session.query(User).filter_by(email=args.user_email).one()
    except NoResultFound:
      if not args.create_user:
        sys.exit("User with email [%s] not found, and --create-user was not specified. Exiting." % args.user_email)
      u = User(email=args.user_email)
      db.session.add(u)
      db.session.commit()
    except MultipleResultsFound:
      raise DatabaseIntegrityError

    try:
      client = db.session.query(OAuthClient).filter_by(user_id=u.id,name=args.name).one()
    except MultipleResultsFound:
      raise DatabaseIntegrityError("Multiple oauthclients found for that user and name")
    except NoResultFound:
      client = OAuthClient(
        user_id = u.id,
        description=args.description,
        name=args.name,
        is_confidential=True,
        is_internal=True,)
      client.gen_salt()
      db.session.add(client)
      db.session.commit()

    try:
      tokens = db.session.query(OAuthToken).filter_by(
        client_id=client.client_id,
        user_id=u.id,
        is_personal=args.is_personal).all()
      #Iterate through each result and compare scopes
      matching_tokens = []
      for t in tokens:
        if set(args.scopes) == set(t.scopes):
          matching_tokens.append(t)
      if not matching_tokens:
        raise NoResultFound
      print "%s tokens with those definitions found, returning the first" % len(matching_tokens)
      token = matching_tokens[0]
    except NoResultFound:
      token = OAuthToken(
        client_id=client.client_id,
        user_id=u.id,
        access_token=gen_salt(current_app.config.get('OAUTH2_TOKEN_PERSONAL_SALT_LEN', 40)),
        refresh_token=gen_salt(current_app.config.get('OAUTH2_TOKEN_PERSONAL_SALT_LEN', 40)),
        _scopes=' '.join(args.scopes),
        expires=datetime.datetime(2050,1,1),
        is_personal=args.is_personal,
        is_internal=True,)
      db.session.add(token)
      db.session.commit()

    return {
      'access_token': token.access_token,
      'refresh_token': token.refresh_token,
      'username': u.email,
      'expires_in': token.expires.isoformat() if token.expires else None,
      'token_type': 'Bearer'}


if __name__=="__main__":
  print '\n'
  print json.dumps(get_token(),indent=1)
