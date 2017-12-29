# -*- coding: utf-8 -*-
"""
    adsws.factory
    ~~~~~~~~~~~~~~~~

    adsws factory module
"""

import os
import warnings
import logging
import logging.handlers

from werkzeug.contrib.fixers import ProxyFix
from flask import g, request, jsonify, session
from flask.ext.login import current_user
from flask.ext.sslify import SSLify
from flask.ext.consulate import Consul, ConsulConnectionError
from adsws.modules.oauth2server.provider import oauth2
from werkzeug.datastructures import Headers

from flask_registry import Registry, ExtensionRegistry, \
    PackageRegistry, ConfigurationRegistry, BlueprintAutoDiscoveryRegistry

from adsmutils import ADSFlask

from .middleware import HTTPMethodOverrideMiddleware


def create_app(app_name=None, instance_path=None, static_path=None,
               static_folder=None, **config):
    """Returns a :class:`Flask` application instance configured with common
    functionality for the AdsWS platform.

    :param app_name: application package name
    :param instance_path: application package path
    :param static_path: flask.Flask static_path kwarg
    :param static_folder: flask.Flask static_folder kwarg
    :param config: a dictionary of settings to override
    """
    # Flask application name
    app_name = app_name or '.'.join(__name__.split('.')[0:-1])

    # Force instance folder to always be located one level above adsws
    instance_path = instance_path or os.path.realpath(os.path.join(
        os.path.dirname(__file__), '../instance'
    ))

    # Create instance path
    try:
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)
    except:
        pass

    if config:
        app = ADSFlask(
            app_name,
            instance_path=instance_path,
            instance_relative_config=False,
            static_path=static_path,
            static_folder=static_folder,
            local_config=config
        )
    else:
        app = ADSFlask(
            app_name,
            instance_path=instance_path,
            instance_relative_config=False,
            static_path=static_path,
            static_folder=static_folder
        )

    # Handle both URLs with and without trailing slashes by Flask.
    app.url_map.strict_slashes = False

    # Ensure SECRET_KEY has a value in the application configuration
    register_secret_key(app)

    # ====================
    # Application assembly
    # ====================
    # Initialize application registry, used for discovery and loading of
    # configuration, extensions and Invenio packages
    Registry(app=app)

    app.extensions['registry'].update(
        # Register packages listed in config
        packages=PackageRegistry(app))

    app.extensions['registry'].update(
        # Register extensions listed in config
        extensions=ExtensionRegistry(app),
        # Register blueprints
        blueprints=BlueprintAutoDiscoveryRegistry(app=app),
    )

    # Extend application config with configuration from packages (app config
    # takes precedence)
    ConfigurationRegistry(app)

    configure_a_more_verbose_log_exception(app)

    app.wsgi_app = HTTPMethodOverrideMiddleware(app.wsgi_app)

    app.before_request(set_translations)
    app.before_request(make_session_permanent)

    if app.config.get('PRODUCTION', False):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            num_proxies=app.config.get('NUM_PROXIES', 2)
        )

    if app.config.get('HTTPS_ONLY', False):
        # Contains the x-forwarded-proto in the criteria already
        # only works if app.debug=False
        # permanent=True responds with 302 instead of 301
        SSLify(app, permanent=True)

    # Register custom error handlers
    if not app.config.get('DEBUG'):
        app.errorhandler(404)(on_404)
        app.errorhandler(401)(on_401)
        app.errorhandler(429)(on_429)
        app.errorhandler(405)(on_405)

    @oauth2.after_request
    def set_adsws_uid_header(valid, oauth):
        """
        If the user is authenticated, inject the header "X-adsws-uid" into
        the incoming request header
        """
        if current_user.is_authenticated():
            h = Headers(request.headers.items())
            h.add_header("X-Adsws-Uid", current_user.id)
            if current_user.ratelimit_level is not None:
                h.add_header(
                    "X-Adsws-Ratelimit-Level",
                    current_user.ratelimit_level
                )
            request.headers = h
        return valid, oauth
    return app


def on_404(e):
    return jsonify(dict(error='Not found')), 404


def on_401(e):
    return jsonify(dict(error='Unauthorized')), 401


def on_429(e):
    return jsonify(dict(error='Too many requests')), 429


def on_405(e):
    return jsonify(dict(error='Method not allowed')), 405


def load_config(app, kwargs_config):
    """
    writes to app.config heiracharchly based on files on disk and consul
    :param app: flask.Flask application instance
    :param kwargs_config: dictionary to update the config
    :return: None
    """

    try:
        app.config.from_object('adsws.config')
    except (IOError, ImportError):
        app.logger.warning("Could not load object adsws.config")
    try:
        app.config.from_object('%s.config' % app.name)
    except (IOError, ImportError):
        app.logger.warning("Could not load object {}.config".format(app.name))

    try:
        f = os.path.join(app.instance_path, 'config.py')
        if os.path.exists(f):
            app.config.from_pyfile(f)
    except IOError:
        app.logger.warning("Could not load {}".format(f))

    try:
        f = os.path.join(app.instance_path, 'local_config.py')
        if os.path.exists(f):
            app.config.from_pyfile(f)
    except IOError:
        app.logger.warning("Could not load {}".format(f))

    try:
        f = os.path.join(app.instance_path, '%s.local_config.py' % app.name)
        if os.path.exists(f):
            app.config.from_pyfile(f)
    except IOError:
        app.logger.warning("Could not load {}".format(f))

    try:
        consul = Consul(app)
        consul.apply_remote_config()
    except ConsulConnectionError:
        app.logger.warning(
            "Could not load config from consul at {}".format(
                os.environ.get('CONSUL_HOST', 'localhost')
            )
        )

    if kwargs_config:
        app.config.update(kwargs_config)

    # old baggage... Consul used to store keys in hexadecimal form
    # so the production/staging databases both convert that into raw bytes
    # but those raw bytes were non-ascii chars (unsafe to pass through
    # env vars). So we must continue converting hex ...
    if app.config.get('SECRET_KEY', None):
        try:
            app.config['SECRET_KEY'] = app.config['SECRET_KEY'].decode('hex')
            app.logger.warning('Converted SECRET_KEY from hex format into bytes')
        except TypeError:
            app.logger.warning('Most likely the SECRET_KEY is not in hex format')



def set_translations():
    """Add under ``g._`` an already configured internationalization function.

    Translations will be returned as unicode objects.
    """
    ## Well, let's make it global now
    def _(s, **kwargs):
        return s % kwargs
    g._ = _


def register_secret_key(app):
    """
    Register sercret key in application configuration., and warns that it
    has not been set properly.
    """
    if app.config.get('SECRET_KEY') is None:
        app.config['SECRET_KEY'] = 'dev'
        warnings.warn("Using insecure dev SECRET_KEY", UserWarning)


def configure_a_more_verbose_log_exception(app):
    """Configure logging."""

    def log_exception(exc_info):
        """
        Override default Flask.log_exception for more verbose logging on
        exceptions.
        """
        try:
            oauth_user = request.oauth
        except AttributeError:
            oauth_user = None

        app.logger.error(
            """
            Request:     {method} {path}
            IP:          {ip}
            Agent:       {agent_platform} | {agent_browser} {agent_browser_version}
            Raw Agent:   {agent}
            Oauth2:      {oauth_user}
            """.format(
                method=request.method,
                path=request.path,
                ip=request.remote_addr,
                agent_platform=request.user_agent.platform,
                agent_browser=request.user_agent.browser,
                agent_browser_version=request.user_agent.version,
                agent=request.user_agent.string,
                oauth_user=oauth_user,
                ), exc_info=exc_info
        )
    app.log_exception = log_exception


def make_session_permanent():
    """
    This will set the expire value on the cookie, thus making it
    persist for as long as app.permanent_session_lifetime (31 days)
    Note that SESSION_REFRESH_EACH_REQUEST (default:True) controls
    if the expiry is refreshed on subsequent visits.
    """
    session.permanent = True
