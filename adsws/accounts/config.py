import os
import logging

BOOTSTRAP_USER_EMAIL = 'anonymous@adslabs.org'
BOOTSTRAP_TOKEN_EXPIRES = 3600*24 #1 day
BOOTSTRAP_SCOPES = []
USER_DEFAULT_SCOPES = ['user']
USER_API_DEFAULT_SCOPES = ['api']
OAUTH2_CLIENT_ID_SALT_LEN = 40
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
CORS_METHODS = ['GET', 'OPTIONS', 'POST', 'PUT']

CACHE = {
  'CACHE_TYPE': 'redis',
  'CACHE_REDIS_HOST': 'localhost',
  'CACHE_REDIS_PORT': 6379,
  'CACHE_REDIS_DB': 0,
  'CACHE_KEY_PREFIX':'accounts_',
}
RATELIMITER_BACKEND = 'flaskcacheredis'

GOOGLE_RECAPTCHA_ENDPOINT = 'https://www.google.com/recaptcha/api/siteverify'
MAIL_DEFAULT_SENDER='no-reply@adslabs.org'
