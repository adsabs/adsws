import os
import logging

SECURITY_REGISTER_BLUEPRINT = False
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

# Stuff that should be added for every application
CORE_PACKAGES = []