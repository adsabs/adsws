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
from collections import namedtuple

from flask import Flask, g
from flask import request
from flask_sslify import SSLify

from flask_registry import Registry, ExtensionRegistry, \
    PackageRegistry, ConfigurationRegistry, BlueprintAutoDiscoveryRegistry

from .middleware import HTTPMethodOverrideMiddleware

def create_app(app_name=None, instance_path=None, static_path=None, static_folder=None, **kwargs_config):
    """Returns a :class:`Flask` application instance configured with common
    functionality for the AdsWS platform.

    :param app_name: application package name
    :param instance_path: application package path
    :param **kwargs: a dictionary of settings to override
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
    except Exception:
        pass
    
    
    app = Flask(app_name, instance_path=instance_path, instance_relative_config=False, static_path=static_path, static_folder=static_folder)
    
    # Handle both URLs with and without trailing slashes by Flask.
    app.url_map.strict_slashes = False

    app.config.from_object('adsws.config')
    try:
        app.config.from_object('%s.config' % app_name)
    except ImportError:
        pass
    app.config.from_pyfile(os.path.join(instance_path, 'config.py'), silent=True)
    app.config.from_pyfile(os.path.join(instance_path, 'local_config.py'), silent=True)
    
    if kwargs_config:
        # Update application config from parameters.
        app.config.update(kwargs_config)

    # Ensure SECRET_KEY has a value in the application configuration
    register_secret_key(app)
    
    # add CORE_ variables to their non-core values
    update_config(app)

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
    
    configure_logging(app)

    app.wsgi_app = HTTPMethodOverrideMiddleware(app.wsgi_app)

    app.before_request(set_translations)

    if app.config.get('PRODUCTION',False):
        app.wsgi_app = ProxyFix(app.wsgi_app,num_proxies=app.config.get('NUM_PROXIES',2))

    if app.config.get('HTTPS_ONLY',False):
        #Contains the x-forwared-proto in the criteria already
        # only works if app.debug=False
        SSLify(app,permanent=True) #permanent=True responds with 302 instead of 301
    
    return app

def set_translations():
    """Add under ``g._`` an already configured internationalization function.

    Translations will be returned as unicode objects.
    """
    ## Well, let's make it global now
    def _(s, **kwargs):
        return s % kwargs
    g._ = _
    
    
def register_secret_key(app):
    """Register sercret key in application configuration."""
    SECRET_KEY = app.config.get('SECRET_KEY') or \
        app.config.get('SITE_SECRET_KEY', 'change_me')

    if not SECRET_KEY or SECRET_KEY == 'change_me':
        fill_secret_key = """
    Set variable SECRET_KEY with random string in instance/local_config.py

    You can use following commands:
    $ %s
        """ % ('python manage.py create-secret-key', )
        warnings.warn(fill_secret_key, UserWarning)

    app.config["SECRET_KEY"] = SECRET_KEY
    

def update_config(app):
    for k, v in app.config.items():
        if k.startswith('CORE_'):
            key = k[5:]
            if key in app.config:
                if isinstance(app.config.get(key), type(v)):
                    if isinstance(v, list):
                        for x in v:
                            app.config.get(key).append(x)
                    elif isinstance(v, dict):
                        app.config.get(key).update(v)
                    else:
                        app.logger.warning('Ignoring overwrite: %s=%s %s=%s'
                                       % (k, v, key, app.config.get(key)))
                else:
                    app.logger.warning('Incompatible type ignored: %s=%s %s=%s'
                                       % (k, v, key, app.config.get(key)))
            else:
                app.config[key] = v

    
def configure_logging(app):
    """Configure logging."""

    try:
        from cloghandler import ConcurrentRotatingFileHandler as RotatingFileHandler
    except ImportError:
        RotatingFileHandler = logging.handlers.RotatingFileHandler 

    def log_exception(exc_info):
        """Override to default Flask.log_exception (more verbose logging on exceptions)"""
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
                method = request.method,
                path = request.path,
                ip = request.remote_addr,
                agent_platform = request.user_agent.platform,
                agent_browser = request.user_agent.browser,
                agent_browser_version = request.user_agent.version,
                agent = request.user_agent.string,
                oauth_user = oauth_user
            ), exc_info=exc_info
        )
    app.log_exception=log_exception

    fn = os.path.join(app.instance_path,app.config.get('LOG_FILE','logs/adsws.log'))
    if not os.path.exists(os.path.dirname(fn)):
      os.makedirs(os.path.dirname(fn))
    rfh = RotatingFileHandler(fn, maxBytes=100000, backupCount=10)
    rfh.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    #NOTE: 
    # Setting the level on just the handler seems to have *no* effect;
    # setting the level on app.logger seems to have the desired effect.
    # I do not understand this behavior
    #rfh.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
    app.logger.setLevel((app.config.get('LOG_LEVEL', logging.INFO)))
    if rfh not in app.logger.handlers:
      app.logger.addHandler(rfh)
    app.logger.debug("Logging initialized")


