BOOTSTRAP_SCOPES = ['ads:default']
BOOTSTRAP_USER_EMAIL = 'anonymous@adslabs.org'
BOOTSTRAP_SALT_LENGTH = 40
BOOTSTRAP_TOKEN_EXPIRES = 3600*24 #1 day

EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',]

PACKAGES = ['adsws.modules.oauth2server',
            'adsws.bumblebee',]
            
CORS_DOMAINS = ['http://localhost:8000',
                'http://localhost:5000',
                'http://adslabs.org',]