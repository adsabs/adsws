import os
import logging

LOG_LEVEL=logging.DEBUG
LOG_FILE='logs/adsws.log' #Relative to here
#Set DEBUG=True to log to stderr, which is useful for development only. 
#Note that this will also print the traceback in the response to the client, which is not desirable in production.
DEBUG=False


BOOTSTRAP_SCOPES = ['ads:default']
BOOTSTRAP_USER_EMAIL = 'anonymous@adslabs.org'
OAUTH2_CLIENT_ID_SALT_LEN = 40
BOOTSTRAP_TOKEN_EXPIRES = 3600*24 #1 day
OAUTH2_CACHE_TYPE='simple'

SECURITY_REGISTER_BLUEPRINT = False
EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',
              'adsws.ext.session',]

PACKAGES = ['adsws.modules.oauth2server',]

CORS_HEADERS = ['Content-Type','X-BB-Api-Client-Version','Authorization','Accept']            
CORS_DOMAINS = ['http://localhost:8000',
                'http://localhost:5000',
                'http://adslabs.org',]
CORS_METHODS = ['GET', 'OPTIONS', 'POST']

CACHE = {
  'CACHE_TYPE': 'redis',
  'CACHE_REDIS_HOST': 'localhost',
  'CACHE_REDIS_PORT': 6379,
  'CACHE_REDIS_DB': 0,
  'CACHE_KEY_PREFIX':'api_',
}
RATELIMITER_BACKEND = 'flaskcacheredis'

WEBSERVICES_PUBLISH_ENDPOINT = 'resources'
WEBSERVICES = {
  # uri : deploy_path
  'http://localhost:4000/': '/vis',
  'http://localhost:1233/citation_helper/':'/citation_helper',
  'http://localhost:1233/graphics/':'/graphics',
  'http://localhost:1233/metrics/':'/metrics',
  'http://localhost:1233/recommender/':'/recommender',
  'adsws.solr.app':'/solr',
  'adsws.graphics.app':'/graphics',
}


SOLR_SEARCH_HANDLER = 'http://localhost:8983/solr/select'
SOLR_QTREE_HANDLER = 'http://localhost:8983/solr/qtree'
SOLR_UPDATE_HANDLER = 'http://localhost:8983/solr/update'
SOLR_TVRH_HANDLER = 'http://localhost:8983/solr/tvrh'

SECRET_KEY = 'fake'
ACCOUNT_VERIFICATION_SECRET = 'fake'

FALL_BACK_ADS_CLASSIC_LOGIN = True
CLASSIC_LOGIN_URL = 'http://adsabs.harvard.edu/cgi-bin/maint/manage_account/credentials'
SITE_SECURE_URL = 'http://0.0.0.0:5000'

# Flask-Sqlalchemy: http://packages.python.org/Flask-SQLAlchemy/config.html
SQLALCHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = 'sqlite:////adsws/adsws.sqlite'

# Stuff that should be added for every application
CORE_PACKAGES = []

HTTPS_ONLY=False