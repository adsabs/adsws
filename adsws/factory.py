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
from flask import Flask

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
        os.path.dirname(inspect.getfile(inspect.currentframe())), '../instance'
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
    app.config.from_envvar('ADSWS_SETTINGS', silent=True)
    app.config.from_envvar('ADSWS_SETTINGS_%s' % (app_name,), silent=True)
    app.config.from_pyfile(os.path.join(instance_path, 'local_config.py'), silent=True)
    
    if kwargs_config:
        # Update application config from parameters.
        app.config.update(kwargs_config)

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
    
    configure_logging(app)

    app.wsgi_app = HTTPMethodOverrideMiddleware(app.wsgi_app)

    return app


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
    
    
def configure_logging(app):
    """Configure file(info) and email(error) logging."""

    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return


    # Set info level on logger, which might be overwritten by handers.
    # Suppress DEBUG messages.
    app.logger.setLevel(logging.INFO)

    info_log = os.path.join(app.instance_path, 'info.log')
    info_file_handler = logging.handlers.RotatingFileHandler(info_log, maxBytes=100000, backupCount=10)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(info_file_handler)