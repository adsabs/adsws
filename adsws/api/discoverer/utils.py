import os
import requests
from werkzeug.security import gen_salt
from flask import request
from views import ProxyView
from adsws.modules.oauth2server.provider import oauth2
from urlparse import urljoin
import traceback
from importlib import import_module
from flask.ext.ratelimiter import ratelimit

_KNOWN_CLIENTS = {
    'vp9a0zwOcx7XJETZyHhC1DwpqGXhKl75iKNCvqSx': "vis-services"
}  # Ugly hack until we have a dynamic rate limits in place


def scope_func(request):
    """
    Finds the correct key with which to attach rate limit on
    :type request: flask.request
    :return: key with which to rate limit on
    """
    if 'X-Forwarded-Authorization' in request.headers:
        # Ugly hack to not track known services while also not
        # double-counting real users. Dynamic rate limits will deprecate this
        if request.oauth.client.client_id in _KNOWN_CLIENTS:
            return "{client}.{random}".format(
                client=request.oauth.client.client_id,
                random=gen_salt(5)
            )
    return request.oauth.client.client_id


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

        # Decorate the view with ratelimit
        if hasattr(attr_base, 'rate_limit'):
            view = ratelimit(
                limit=attr_base.rate_limit[0],
                per=attr_base.rate_limit[1],
                scope_func=lambda: scope_func(request),
                key_func=lambda: request.endpoint
            )(view)

        # Decorate the view with require_oauth
        if hasattr(attr_base, 'scopes'):
            view = oauth2.require_oauth(*attr_base.scopes)(view)

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
    url = urljoin(
        service_uri,
        app.config.get('WEBSERVICES_PUBLISH_ENDPOINT', '/')
    )

    try:
        r = requests.get(url,timeout=5)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        app.logger.info('Could not discover {0}'.format(service_uri))
        return

    # validate(r.json()) # TODO validate the incoming json

    # Start constructing the ProxyViews based on what we got when querying
    # the /resources route.
    # If any part of this procedure fails, log that we couldn't produce this
    # ProxyView, but otherwise continue.
    for resource, properties in r.json().iteritems():
        if resource.startswith('/'):
            resource = resource[1:]
        route = os.path.join(deploy_path, resource)
        remote_route = urljoin(service_uri, resource)

        # Make an instance of the ProxyView. We need to instantiate the class
        # to save instance attributes, which will be necessary to re-construct
        # the location to the third party resource (ProxyView.endpoint)
        proxyview = ProxyView(remote_route, service_uri, deploy_path)

        for method in properties['methods']:
            if method not in proxyview.methods:
                app.logger.warning("Could not create a ProxyView for method %s for %s" % (method,service_uri))
                continue

            view = proxyview.dispatcher

            # Decorate the view with ratelimit.
            # We should fail if the remote app does not define rate_limit
            view = ratelimit(
                limit = properties['rate_limit'][0],
                per= properties['rate_limit'][1],
                scope_func=lambda: scope_func(request),
                key_func=lambda: request.endpoint,
            )(view)

            # Decorate with the advertised oauth2 scopes
            # We should fail if the remote app does not define scopes
            view = oauth2.require_oauth(*properties['scopes'])(view)

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
            if service_uri.startswith('http'):
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
