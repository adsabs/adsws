EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',]

PACKAGES = ['adsws.discoverer', 'adsws.modules.oauth2server',]

WEBSERVICES_PUBLISH_ENDPOINT = '/resources'
WEBSERVICES = {
  # uri : deploy_path
  'http://localhost:4000':'/sample_application',
  'http://localhost:3999':'/graphics',
}
