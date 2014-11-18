SOLR_SEARCH_HANDLER = 'http://localhost:9000/solr/select'
SOLR_QTREE_HANDLER = 'http://localhost:9000/solr/qtree'
SOLR_UPDATE_HANDLER = 'http://localhost:9000/solr/update'
SOLR_TVRH_HANDLER = 'http://localhost:9000/solr/tvrh'

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
                'http://localhost:5000': 1,
                'http://adslabs.org': 1
                }

VERSION = 'v1'

# what is the rate of requests per day
MAX_RATE_LIMITS = {
    'default': 20000, # authenticated users
    'anonymous@adslabs.org': 500
}

MAX_RATE_EXPIRES_IN = 3600 * 24