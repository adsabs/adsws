EXTENSIONS = [
    'adsws.ext.sqlalchemy',
    'adsws.ext.security',
    'adsws.ext.ratelimiter',
]

PACKAGES = ['adsws.modules.oauth2server', ]

SECURITY_REGISTER_BLUEPRINT = True
SECURITY_REGISTERABLE = True
SECURITY_CONFIRMABLE = True

# 30 days expiration
OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 30*24*3600
