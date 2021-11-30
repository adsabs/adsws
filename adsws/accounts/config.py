LOG_LEVEL = 30 # To be deprecated when all microservices use ADSFlask
LOGGING_LEVEL = "INFO"
LOG_STDOUT = True
BOOTSTRAP_USER_EMAIL = 'anonymous@ads'
BOOTSTRAP_TOKEN_EXPIRES = 3600*24  # 1 day
BOOTSTRAP_SCOPES = []
USER_DEFAULT_SCOPES = ['user']
USER_API_DEFAULT_SCOPES = ['api']
OAUTH2_CLIENT_ID_SALT_LEN = 40
OAUTH2_CACHE_TYPE = 'simple'

SECURITY_REGISTER_BLUEPRINT = False
EXTENSIONS = [
    'adsws.ext.menu',
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
    'X-CSRFToken',
]

CORS_DOMAINS = [
    'http://localhost:8000',
]

CORS_METHODS = ['GET', 'OPTIONS', 'POST', 'PUT']

RATELIMIT_STORAGE_URL = "redis://localhost:6379"
RATELIMIT_HEADERS_ENABLED = True
RATELIMIT_SWALLOW_ERRORS = True
RATELIMIT_KEY_PREFIX = "limiter"

GOOGLE_RECAPTCHA_ENDPOINT = 'https://www.google.com/recaptcha/api/siteverify'
MAIL_DEFAULT_SENDER = 'no-reply@adslabs.org'

PASSWORD_RESET_URL = 'https://ui.adsabs.harvard.edu/#user/account/verify/reset-password'
