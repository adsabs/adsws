EXTENSIONS = [
  'adsws.ext.menu',
  'adsws.ext.sqlalchemy',
]

PACKAGES = [
  'adsws.modules.oauth2server',
]



WEBSERVICES_PUBLISH_ENDPOINT = 'resources'
WEBSERVICES = {
  # uri : deploy_path
  'http://localhost:4000/': '/vis',
  'http://localhost:1233/citation_helper/':'/citation_helper',
  'http://localhost:1233/graphics/':'/graphics',
  'http://localhost:1233/metrics/':'/metrics',
  'http://localhost:1233/recommender/':'/recommender',
#  'adsws.sample_application.app': '/sample_application',
}

CORS_HEADERS = ['Content-Type','X-BB-Api-Client-Version','Authorization','Accept']
