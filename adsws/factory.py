# -*- coding: utf-8 -*-
"""
    adsws.factory
    ~~~~~~~~~~~~~~~~

    adsws factory module
"""

import os
import warnings
import inspect
import logging
import logging.handlers
from collections import namedtuple

from flask import Flask, g

from flask_registry import Registry, ExtensionRegistry, \
    PackageRegistry, ConfigurationRegistry, BlueprintAutoDiscoveryRegistry

from .middleware import HTTPMethodOverrideMiddleware

class AttributeDict(dict):
    def __getattr__(self, name):
        return self[name]

def create_app(app_name=None, instance_path=None, **kwargs_config):
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
        get_root_path(), '../instance'
    ))
    
    # Create instance path
    try:
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)
    except Exception:
        pass
    
    
    app = Flask(app_name, instance_path=instance_path, instance_relative_config=False)
    
    # Handle both URLs with and without trailing slashes by Flask.
    app.url_map.strict_slashes = False

    app.config.from_object('adsws.config')
    try:
        app.config.from_object('%s.config' % app_name)
    except ImportError:
        pass
    app.config.from_pyfile(os.path.join(instance_path, 'local_config.py'), silent=True)
    app.config.from_envvar('ADSWS_SETTINGS', silent=True)
    app.config.from_envvar('ADSWS_SETTINGS_%s' % (app_name,), silent=True)
    
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
    
    return app

def get_root_path():
    return os.path.dirname(inspect.getfile(inspect.currentframe()))

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
        
    fn = os.path.join(app.instance_path,app.config.get('LOG_FILE','logs/adsws.log'))
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


