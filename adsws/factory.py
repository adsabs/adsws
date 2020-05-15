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
from flask import g, request, jsonify, session, current_app
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

    app = ADSFlask(
        app_name,
        instance_path=instance_path,
        instance_relative_config=False,
        static_path=static_path,
        static_folder=static_folder,
        local_config=config or {}
    )

    # Handle both URLs with and without trailing slashes by Flask.
    app.url_map.strict_slashes = False

    load_config(app, config)

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
    app.before_request(cache_data_stream)

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
        h = Headers(request.headers.items())
        
        if current_user.is_authenticated():
            h.add_header("X-Adsws-Uid", current_user.id)
        elif h.has_key("X-Adsws-Uid"):
            h.remove("X-Adsws-Uid") # being paranoid
            
        if valid:    
            level = oauth.client.ratelimit
            if level is None:
                level = 1.0
            h.add_header("X-Adsws-Ratelimit-Level", level)
        else:
            h.add_header("X-Adsws-Ratelimit-Level", 0.0)
        
        request.headers = h
        return valid, oauth
    
    @app.teardown_request
    def teardown_request(exception=None):
        """This function will close active transaction, if there is one
        but only if the session is not dirty - we don't want to do any
        magic (instead of a developer)
        
        use expire_on_commit=False doesn't have the same effect
        http://docs.sqlalchemy.org/en/latest/orm/session_api.html#sqlalchemy.orm.session.Session.commit
        
        The problems we are facing is that a new transaction gets opened
        when session is committed; consequent access to the ORM objects
        opens a new transaction (which never gets closed and is rolled back)
        """
        a = current_app
        if 'sqlalchemy' in a.extensions: # could use self.db but let's be very careful
            sa = a.extensions['sqlalchemy']
            if hasattr(sa, 'db') and hasattr(sa.db, 'session') and sa.db.session.is_active:
                if bool(sa.db.session.dirty):
                    sa.db.session.close() # db server will do rollback
                else:
                    sa.db.session.commit() # normal situation
                
    return app


def on_404(e):
    return jsonify(dict(error='Not found')), 404


def on_401(e):
    return jsonify(dict(error='Unauthorized')), 401


def on_429(e):
    return jsonify(dict(error='Too many requests')), 429


def on_405(e):
    return jsonify(dict(error='Method not allowed')), 405

def __load_config(app, method_name, method_argument):
    """
    Load configuration into the application using the method
    `from_object` or `from_pyfile` with the argument pointing
    to a python object or a python filename.
    """
    if method_name not in ("from_object", "from_pyfile"):
        raise Exception("Unsupported method: '{}'".format(method_name))
    # Load config but give preference to values loaded from
    # main config file as loaded by ADSFlask
    import flask
    try:
        config = flask.config.Config(app.config['PROJ_HOME'])
        method_to_call = getattr(config, method_name)
        method_to_call(method_argument)
        config.update(app.config)
        app.config = config
    except (IOError, ImportError):
        app.logger.warning("Could not load config (%s): %s", method_name, method_argument)

def load_config(app, kwargs_config):
    """
    writes to app.config heiracharchly based on files on disk
    :param app: flask.Flask application instance
    :param kwargs_config: dictionary to update the config
    :return: None
    """

    __load_config(app, 'from_object', '%s.config' % app.name)

    f = os.path.join(app.instance_path, 'config.py')
    if os.path.exists(f):
        __load_config(app, 'from_pyfile', f)

    f = os.path.join(app.instance_path, 'local_config.py')
    if os.path.exists(f):
        __load_config(app, 'from_pyfile', f)

    f = os.path.join(app.instance_path, '%s.local_config.py' % app.name)
    if os.path.exists(f):
        __load_config(app, 'from_pyfile', f)

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


def cache_data_stream():
    """Workaround for remembering the input stream data (i.e. input stream
    will be saved/cached and can be retrieved.
    
    The problem is following:
        - request.attributes are initialized the first time they are used
        
        - flask_oauthlib is the first one to call request
            request.form.to_dict()
        - but stream is *only* cached if request.get_data() was 
          called first
        - if you call request.form, the stream is read and it can
          never be retrieved again (it is a socked)
          
    Important detail: always set MAX_CONTENT_LENGTH
    """
    cl = request.content_length
    ml = current_app.config.get('MAX_CONTENT_LENGTH', 1024*1024*5)
    if ml is None or ml > cl:
        request.get_data(cache=True, as_text=False, parse_form_data=False)


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
