# -*- coding: utf-8 -*-
"""
    adsws.discoverer
    ~~~~~~~~~~~~~~~~~~

"""
import os
from .. import factory
import requests
from flask import current_app
from views import ProxyView, StatusView
from flask.ext.restful import Api
from adsws.modules.oauth2server.provider import oauth2
from urlparse import urljoin

def discover(app):
  for service_uri, deploy_path in app.config.get('WEBSERVICES',{}).iteritems():
    url = urljoin(service_uri,app.config.get('WEBSERVICES_PUBLISH_ENDPOINT',''))
    r = requests.get(url)
    #validate(r.json())
    for resource, properties in r.json().iteritems():
      if resource.startswith('/'):
        resource = resource[1:]
      route = os.path.join(deploy_path,resource)
      remote_route = urljoin(service_uri,resource)
      print remote_route
      view = ProxyView(remote_route)
      app.add_url_rule(route,route,view.get)


def create_app(**kwargs_config):
  app = factory.create_app(__name__, **kwargs_config)
  api = Api(app)
  api.add_resource(StatusView,'/status')
  discover(app)
  return app


if __name__ == '__main__':
  app = Flask(__name__)
  app.run('0.0.0.0',5000,debug=True) 

