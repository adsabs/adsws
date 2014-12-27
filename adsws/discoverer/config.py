EXTENSIONS = [
  'adsws.ext.menu',
  'adsws.ext.sqlalchemy',
]

PACKAGES = [
  'adsws.modules.oauth2server',
]


CACHE = {
  'CACHE_TYPE': 'redis',
  'CACHE_REDIS_HOST': 'localhost',
  'CACHE_REDIS_PORT': 6379,
  'CACHE_REDIS_DB': 0,
  'CACHE_KEY_PREFIX':'adsws_',
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
  'adsws.solr.app':'/search',
}

CORS_HEADERS = ['Content-Type','X-BB-Api-Client-Version','Authorization','Accept']
