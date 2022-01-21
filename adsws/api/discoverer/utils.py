import os
import requests
import json
import re
import Cookie
from flask_headers import headers
from flask import request
from views import ProxyView
from adsws.modules.oauth2server.provider import oauth2
from urlparse import urljoin
import traceback
from importlib import import_module
from adsws.ext.ratelimiter import ratelimit, limit_func, scope_func, key_func
from flask_consulate import ConsulService
from functools import wraps
from .affinity import affinity_decorator

def local_app_context(local_app):
    """
    Ensure that an imported view is run under the correct application context
    """
    def real_local_app_context_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            with local_app.app_context():
                return f(*args, **kwargs)
        return decorated_function
    return real_local_app_context_decorator

def bootstrap_local_module(service_uri, deploy_path, app):
    """
    Incorporates the routes of an existing app into this one
    :param service_uri: the path to the target application
    :param deploy_path: the path on which to make the target app discoverable
    :param app: flask.Flask application instance
    :return: None
    """

    app.logger.debug(
        'Attempting bootstrap_local_module [{0}]'.format(service_uri)
    )

    module = import_module(service_uri)
    local_app = module.create_app()

    # Add the target app's config to the parent app's config.
    # Do not overwrite any config already present in the parent app
    for k, v in local_app.config.iteritems():
        if k not in app.config:
            app.config[k] = v

    for rule in local_app.url_map.iter_rules():
        view = local_app.view_functions[rule.endpoint]
        route = os.path.join(deploy_path, rule.rule[1:])

        # view_class is attached to a function view in the case of
        # class-based views, and that view.view_class is the element
        # that has the scopes and docstring attributes
        if hasattr(view, 'view_class'):
            attr_base = view.view_class
        else:
            attr_base = view

        # ensure the current_app matches local_app and not API app
        view = local_app_context(local_app)(view)

        if deploy_path in local_app.config.get('AFFINITY_ENHANCED_ENDPOINTS', []):
            view = affinity_decorator(ratelimit._storage.storage, name=local_app.config['AFFINITY_ENHANCED_ENDPOINTS'].get(deploy_path))(view)


        # Decorate the view with ratelimit
        if hasattr(attr_base, 'rate_limit'):

            # collect symbolic ratelimits
            _update_symbolic_ratelimits(app, route, {'rate_limit': attr_base.rate_limit})

            # create local (default) ratelimits
            d = attr_base.rate_limit[0]
            view = ratelimit.shared_limit_and_check(
                lambda counts=d, per_second=attr_base.rate_limit[1]: limit_func(counts, per_second),
                scope=scope_func,
                key_func=key_func,
                methods=rule.methods,
                per_method=False
            )(view)

        # Decorate the view with require_oauth
        if hasattr(attr_base, 'scopes'):
            view = oauth2.require_oauth(*attr_base.scopes)(view)

        # Add cache-control headers
        if app.config.get('API_PROXYVIEW_HEADERS'):
            view = headers(app.config['API_PROXYVIEW_HEADERS'])(view)

        # Let flask handle OPTIONS, which it will not do if we explicitly
        # add it to the url_map
        if 'OPTIONS' in rule.methods:
            rule.methods.remove('OPTIONS')
        app.add_url_rule(route, route, view, methods=rule.methods)



def bootstrap_remote_service(service_uri, deploy_path, app):
    """
    Incorporates the routes of a remote app into this one by registering
    views that forward traffic to those remote endpoints
    :param service_uri: the http url of the target application
    :param deploy_path: the path on which to make the target app discoverable
    :param app: flask.Flask application instance
    :return: None
    """

    app.logger.debug(
        'Attempting bootstrap_remote_service [{0}]'.format(service_uri)
    )

    if service_uri.startswith('consul://'):
        cs = ConsulService(
            service_uri,
            nameservers=[app.config.get("CONSUL_DNS", "172.17.42.1")]
        )
        url = urljoin(
            cs.base_url,
            app.config.get('WEBSERVICES_PUBLISH_ENDPOINT', '/')
        )
        print "base url", cs.base_url
    else:
        url = urljoin(
            service_uri,
            app.config.get('WEBSERVICES_PUBLISH_ENDPOINT', '/')
        )

    cache_key = service_uri.replace('/', '').replace('\\', '').replace('.', '')
    cache_dir = app.config.get('WEBSERVICES_DISCOVERY_CACHE_DIR', '')
    cache_path = os.path.join(cache_dir, cache_key)
    resource_json = {}

    # discover the ratelimits/urls/permissions from the service itself;
    # if not available, use a cached values (if any)
    try:
        r = requests.get(url, timeout=5)
        resource_json = r.json()
        if cache_dir:
            try:
                with open(cache_path, 'w') as cf:
                    cf.write(json.dumps(resource_json))
            except IOError:
                app.logger.error('Cant write cached resource {0}'.format(cache_path))
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if cache_dir and os.path.exists(cache_path):
            with open(cache_path, 'r') as cf:
                resource_json = json.loads(cf.read())
        else:
            app.logger.info('Could not discover {0}'.format(service_uri))
            return



    # Start constructing the ProxyViews based on what we got when querying
    # the /resources route.
    # If any part of this procedure fails, log that we couldn't produce this
    # ProxyView, but otherwise continue.
    for resource, properties in resource_json.iteritems():

        properties.setdefault('rate_limit', [1000, 86400])
        properties.setdefault('scopes', [])

        if resource.startswith('/'):
            resource = resource[1:]
        route = os.path.join(deploy_path, resource)
        remote_route = urljoin(service_uri, resource)

        # Make an instance of the ProxyView. We need to instantiate the class
        # to save instance attributes, which will be necessary to re-construct
        # the location to the third party resource (ProxyView.endpoint)
        with app.app_context():
            # app_context to allow config lookup via current_app in __init__
            proxyview = ProxyView(remote_route, service_uri, deploy_path, route)


        _update_symbolic_ratelimits(app, route, properties)



        for method in properties['methods']:
            if method not in proxyview.methods:
                app.logger.warning("Could not create a ProxyView for "
                                   "method {meth} for {ep}"
                                   .format(meth=method, ep=service_uri))
                continue

            view = proxyview.dispatcher

            # Decorate the view with ratelimit.
            d = properties['rate_limit'][0]
            view = ratelimit.shared_limit_and_check(
                lambda counts=d, per_second=properties['rate_limit'][1]: limit_func(counts, per_second),
                scope=scope_func,
                key_func=key_func,
                methods=[method],
                per_method=False
            )(view)

            if deploy_path in app.config.get('AFFINITY_ENHANCED_ENDPOINTS', []):
                view = affinity_decorator(ratelimit._storage.storage, name=app.config['AFFINITY_ENHANCED_ENDPOINTS'].get(deploy_path))(view)

            # Decorate with the advertised oauth2 scopes
            view = oauth2.require_oauth(*properties['scopes'])(view)

            # Add cache-control headers
            if app.config.get('API_PROXYVIEW_HEADERS'):
                view = headers(app.config['API_PROXYVIEW_HEADERS'])(view)

            # Either make a new route with this view, or append the new method
            # to an existing route if one exists with the same name
            try:
                rule = next(app.url_map.iter_rules(endpoint=route))
                if method not in rule.methods:
                    rule.methods.update([method])
            except KeyError:
                app.add_url_rule(route, route, view, methods=[method])


def discover(app):
    """
    Query each third-party service defined in the config for a route that
    advertises that app's resources ('/resources' by default). Incorporate that
    app's routes into the api app, either directly (local module) or via
    proxying to a remote endpoint

    :param app: flask.Flask application instance
    :return: None
    """

    webservices = app.config.get('WEBSERVICES')
    if not webservices:
        webservices = {}
    for service_uri, deploy_path in webservices.iteritems():
        try:
            if any([
                    service_uri.startswith(prefix) for prefix in
                    ['http://', 'https://', 'consul://']
                    ]):
                bootstrap_remote_service(service_uri, deploy_path, app)
            else:
                bootstrap_local_module(service_uri, deploy_path, app)
        except:  # Continue bootstrapping, but log the traceback
            app.logger.error(
                "Problem discovering {service}, skipping this service "
                "entirely: {traceback}".format(
                    service=service_uri,
                    traceback=traceback.format_exc()
                )
            )


def _update_symbolic_ratelimits(app, route, properties):
    """Build information about ratelimit groups; this data
    is used for ratelimiting endpoints that should share
    ratelimit counters.

    All the info is stored in the current application
    (which is a global object)
    """

    symbolic_ratelimits = app.extensions['symbolic_ratelimits'] #fail if not properly initiated

    if route in symbolic_ratelimits:
        return # already there


    # check if the remote endpoint ratelimit should belong to a
    # virtual ratelimit group (and build the info accordingly)
    for ratelimit_group, values in app.config.get('RATELIMIT_GROUPS', {}).items():


        # if not supplied, we'll use limits of the endpoint
        count, per_second = isinstance(values, dict) and values.get('limits', [properties['rate_limit'][0], properties['rate_limit'][1]]) \
            or [properties['rate_limit'][0], properties['rate_limit'][1]]


        endpoint_patterns = isinstance(values, dict) and values.get('patterns', []) or values

        for pattern_num, pattern in enumerate(endpoint_patterns):
            try:
                p = re.compile(pattern)
                if p.match(route):
                    app.logger.info("Endpoint {endpoint} will belong to a virtual ratelimit {group}"
                                    .format(endpoint=route, group=ratelimit_group))
                    if ratelimit_group not in symbolic_ratelimits:
                        symbolic_ratelimits[ratelimit_group] = {'key': ratelimit_group,
                                                                '#': pattern_num,
                                                                'count': count,
                                                                'per_second': per_second}

                    pointer = symbolic_ratelimits[ratelimit_group]
                    symbolic_ratelimits[route] = pointer

                    # lower orders have higher priority (over-riding ratelimits)
                    # it matters only when ratelimits were not explicitly configured
                    if pattern_num < pointer['#']:
                        pointer['count'] = count
                        pointer['per_second'] = per_second

                    break

            except:
                app.logger.error("Error compiling regex {regex} for ratelimit {group}"
                                 .format(regex=pattern, group=ratelimit_group))
