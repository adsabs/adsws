BOOTSTRAP_SCOPES = ['ads:default']
BOOTSTRAP_USER_EMAIL = 'anonymous@adslabs.org'
OAUTH2_CLIENT_ID_SALT_LEN = 40
BOOTSTRAP_TOKEN_EXPIRES = 3600*24 #1 day

EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',]

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
