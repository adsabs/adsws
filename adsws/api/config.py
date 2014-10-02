SOLR_SEARCH_HANDLER = 'http://localhost:9000/solr/select'
SOLR_QTREE_HANDLER = 'http://localhost:9000/solr/qtree'
SOLR_UPDATE_HANDLER = 'http://localhost:9000/solr/update'

ANONYMOUS_USER = 'anonymous@adslabs.org'

EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',]

PACKAGES = ['adsws.modules.oauth2server',
            'adsws.api',
            'adsws.api.solr',
            'adsws.api.bumblebee']

CORS_DOMAINS = {
                'http://localhost:8000': 1,
                'http://adslabs.org': 1
                }

VERSION = 'v1'

# what is the rate of requests per day
MAX_RATE_LIMITS = {
    'default': 10000, # authenticated users
    'anonymous@adslabs.org': 1000
}

MAX_RATE_EXPIRES_IN = 3600 * 24