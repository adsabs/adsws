LOG_STDOUT = True
SECURITY_REGISTER_BLUEPRINT = False
EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',
              'adsws.ext.ratelimiter',
]

PACKAGES = ['adsws.modules.oauth2server', ]

CORS_HEADERS = [
    'Content-Type',
    'X-BB-Api-Client-Version',
    'Authorization',
    'Accept',
]
CORS_DOMAINS = [
    'http://localhost:8000',
    'http://localhost:5000',
    'http://adslabs.org',
]
CORS_METHODS = ['GET', 'OPTIONS', 'POST']

RATELIMIT_STORAGE_URL = "redis://localhost:6379"
RATELIMIT_HEADERS_ENABLED = True
RATELIMIT_SWALLOW_ERRORS = True
RATELIMIT_KEY_PREFIX = "limiter"

