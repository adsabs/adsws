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
    '--target-date',
    required=False,
    default=datetime.datetime.now(),
    dest='date',
    type=lambda s: datetime.datetime.strptime(s,'%Y-%m-%dT%H:%M:%S'),
    help='Target date to compare against (format %%Y-%%m-%%dT%%H:%%M:%%S); defaults to datetime.now()'
    )

def main():
  parser = argparse.ArgumentParser()
  add_arguments(parser)
  args = parser.parse_args()
  app = create_app('manual_client_registration',
    EXTENSIONS = ['adsws.ext.sqlalchemy',
                  'adsws.ext.security',],
    PACKAGES=['adsws.modules.oauth2server',])

  with app.app_context():
    for token in db.session.query(OAuthToken).filter(OAuthToken.expires <= args.date).all():
      db.session.delete(token)
    db.session.commit()


if __name__=="__main__":
  main()