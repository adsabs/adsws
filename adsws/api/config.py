SOLR_SEARCH_HANDLER = 'http://localhost:9000/solr/select'
SOLR_UPDATE_HANDLER = 'http://localhost:9000/solr/update'

ANONYMOUS_USER = 'anonymous@adslabs.org'

EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',]

PACKAGES = ['adsws.modules.oauth2server',
            'adsws.api.solr',
            'adsws.api.bumblebee']

CORS_DOMAINS = {
                'http://localhost:8000': 1,
                'http://adslabs.org': 1
                }