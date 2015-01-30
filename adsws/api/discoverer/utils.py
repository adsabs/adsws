import os, sys
import requests
from flask import current_app, request
from views import ProxyView
from adsws.modules.oauth2server.provider import oauth2
from urlparse import urljoin
import traceback
from importlib import import_module
from flask.ext.ratelimiter import ratelimit

def bootstrap_local_module(service_uri,deploy_path,app):
  '''
  Incorporates the routes of an existing app into this one
  '''
  app.logger.debug('Attempting bootstrap_local_module [%s]' % service_uri)

  module = import_module(service_uri)
  local_app=module.create_app()

  for k,v in local_app.config.iteritems():
    if k not in app.config:
      app.config[k] = v

  for rule in local_app.url_map.iter_rules():
    view = local_app.view_functions[rule.endpoint]
    route = os.path.join(deploy_path,rule.rule[1:])
    if view.view_class.rate_limit:
      params = view.view_class.rate_limit
      defaults = {
          'scope_func':lambda: request.oauth.client.client_id,
          'key_func': lambda: route,
      }
      view = ratelimit(params[0],
        per=          params[1],
        scope_func=   defaults['scope_func'],
        key_func=     defaults['key_func'])(view)
    if hasattr(view.view_class,'scopes'):
      view = oauth2.require_oauth(*view.view_class.scopes)(view)
    app.add_url_rule(route,route,view)

def bootstrap_remote_service(service_uri,deploy_path,app):
  app.logger.debug('Attempting bootstrap_remote_service [%s]' % service_uri)
  url = urljoin(service_uri,app.config.get('WEBSERVICES_PUBLISH_ENDPOINT',''))
  try:
    r = requests.get(url,timeout=5)
  except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
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

      params = properties['rate_limit']
      if params:
        defaults = {
            'scope_func':lambda: request.oauth.client.client_id,
            'key_func': lambda: route,
        }
        view = ratelimit(params[0],
          per=          params[1],
          scope_func=   defaults['scope_func'],
          key_func=     defaults['key_func'])(view)

      #Decorate with the service-defined oauth2 scopes
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
  '''Query each third-party service defined in the config for a route ('resources' by default)
  This route is expected to be present in all web-services, and describes which routes are present
  therein.'''
  WEBSERVICES = app.config.get('WEBSERVICES')
  if not WEBSERVICES:
    WEBSERVICES = {}
  for service_uri, deploy_path in WEBSERVICES.iteritems():
    try:
      if service_uri.startswith('http'):
        bootstrap_remote_service(service_uri,deploy_path,app)
      else:
        bootstrap_local_module(service_uri,deploy_path,app)
    except:
      app.logger.warning("Problem discovering %s, skipping this service entirely: %s" % (service_uri,traceback.format_exc()))
