# -*- coding: utf-8 -*-
"""
    adsws.discoverer
    ~~~~~~~~~~~~~~~~~~

"""
import os
from .. import factory
import requests
from flask import current_app, request
from views import ProxyView, StatusView
from flask.ext.restful import Api
from flask.ext.cors import CORS
from adsws.modules.oauth2server.provider import oauth2
from urlparse import urljoin
import traceback
from importlib import import_module
from flask.ext.ratelimiter import RateLimiter, ratelimit
from flask.ext.cache import Cache


def bootstrap_local_module(service_uri,deploy_path,app):
  module = import_module(service_uri)
  local_app=module.create_app()

  for rule in local_app.url_map.iter_rules():
    view = local_app.view_functions[rule.endpoint]
    route = os.path.join(deploy_path,rule.rule[1:])
    if view.view_class.rate_limit:
      params = view.view_class.rate_limit
      if len(params) < 3:
        defaults = {
          'scope_func':lambda: request.oauth.client_id,
          'key_func': lambda: route,
        }
        params.append(defaults)
      view = ratelimit(params[0],
        per=          params[1],
        scope_func=   params[2].get('scope_func',defaults['scope_func']),
        key_func=     params[2].get('key_func',defaults['key_func']))(view)
    if hasattr(view.view_class,'scopes'):
      view = oauth2.require_oauth(*view.view_class.scopes)(view)
    app.add_url_rule(route,route,view)

def bootstrap_remote_service(service_uri,deploy_path,app):
  url = urljoin(service_uri,app.config.get('WEBSERVICES_PUBLISH_ENDPOINT',''))
  try:
    r = requests.get(url)
  except requests.exceptions.ConnectionError:
    app.logger.info('Could not discover %s' % service_uri)
    return

  #validate(r.json()) #TODO; validate

  #Start constructing the ProxyViews based on what we got when querying
  #the /resources route.
  # If any part of this procedure fails, log that we couldn't produce this ProxyView
  # but otherwise fail silently.
  for resource, properties in r.json().iteritems():
    if resource.startswith('/'):
      resource = resource[1:]
    route = os.path.join(deploy_path,resource)
    remote_route = urljoin(service_uri,resource)

    #Make an instance of the ProxyView. We need to instantiate the class to save
    #instance attributes, which will be necessary to re-construct the location to the
    #third party resource.
    proxyview = ProxyView(remote_route,service_uri,deploy_path)

    for method in properties['methods']:
      if method not in proxyview.methods:
        app.logger.warning("Could not create a ProxyView for method %s for %s" % (method,service_uri))
        continue  
      view = proxyview._dispatcher

      #Decorate with the service-defined oauth2 scopes
      if properties['scopes']:
        view = oauth2.require_oauth(*properties['scopes'])(view)
      
      #Either make a new route with this view, or append the new method to an existing route
      #that has the same name
      try:
        rule = next(app.url_map.iter_rules(endpoint=route))
        if method not in rule.methods:
          rule.methods.update([method])
      except KeyError:
        app.add_url_rule(route,route,view,methods=[method])


def discover(app):
  #Query each third-party service defined in the config for a route ('resources' by default)
  #This route is expected to be present in all web-services, and describes which routes are present
  #therein.
  for service_uri, deploy_path in app.config.get('WEBSERVICES',{}).iteritems():
    try:
      if service_uri.startswith('http'):
        bootstrap_remote_service(service_uri,deploy_path,app)
      else:
        bootstrap_local_module(service_uri,deploy_path,app)    
    except:
      app.logger.warning("Problem discovering %s, skipping this service entirely: %s" % (service_uri,traceback.format_exc()))


def create_app(**kwargs_config):
  app = factory.create_app(__name__.replace('.app',''),**kwargs_config)
  
  api = Api(app)
  ratelimiter = RateLimiter(app=app)
  cors = CORS(app,origins=app.config.get('CORS_DOMAINS'), headers=app.config.get('CORS_HEADERS'))
  cache = Cache(app,config=app.config['CACHE'])
  
  api.add_resource(StatusView,'/status')
  discover(app)

  for rule in app.url_map.iter_rules():
    print rule.rule
  return app


if __name__ == '__main__':
  app = Flask(__name__)
  app.run('0.0.0.0',5000,debug=True) 
