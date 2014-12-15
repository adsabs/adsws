# -*- coding: utf-8 -*-
"""
    adsws.api
    ~~~~~~~~~~~~~

    adsws api application package
"""

from functools import wraps

from flask import jsonify, current_app, Response, make_response,\
    request, abort

from ..core import AdsWSError, AdsWSFormError, JSONEncoder
from .. import factory
from .models import OAuthClientLimits
from datetime import datetime, timedelta

from flask.ext.ratelimiter import RateLimiter

def create_app(**kwargs_config):
    """Returns the AdsWS API application instance"""

    app = factory.create_app(app_name=__name__, **kwargs_config)
    ext = RateLimiter(app=app)

    # Set the default JSON encoder
    app.json_encoder = JSONEncoder

    # Register custom error handlers
    if not app.config.get('DEBUG'):
        app.errorhandler(AdsWSError)(on_adsws_error)
        app.errorhandler(AdsWSFormError)(on_adsws_form_error)
        app.errorhandler(404)(on_404)
        app.errorhandler(401)(on_401)

    if app.config.get('CUSTOM_HEADERS'):
        @app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
    
    return app


def route(bp, *args, **kwargs):
    kwargs.setdefault('strict_slashes', False)
    
    methods = 'GET, POST, OPTIONS, HEAD'
    if 'methods' in kwargs:
        kwargs['methods'].append('OPTIONS')
        methods = ', '.join(sorted(x.upper() for x in kwargs['methods']))
        
    def decorator(f):
        @bp.route(*args, **kwargs)
        @wraps(f)
        def wrapper(*args, **kwargs):
            
            response = rv = None
            sc = 200
            to_add = []
            
            if (request.method == "OPTIONS"):
                to_add.append(("Access-Control-Allow-Methods", methods))
                # Allow a max age of one day
                to_add.append(("Access-Control-Max-Age", 24 * 3600))
                
                if request.headers.get('Access-Control-Request-Headers'):
                    to_add.append(("Access-Control-Allow-Headers", request.headers.get('Access-Control-Request-Headers')))
            else:
                rv = f(*args, **kwargs)
            
            
            
            if isinstance(rv, tuple):
                response = make_response(rv[0], rv[1])
            elif isinstance(rv, Response):
                response = rv
            elif isinstance(rv, basestring):
                response = make_response(rv, sc) # assuming it is a json string
            elif isinstance(rv, dict):
                response = make_response(jsonify(rv), sc)
            else:
                response = make_response(jsonify(dict(data=rv)), sc)
            
            if current_app.config.get('CORS_DOMAINS', None):
                if request.headers.get('Origin') in current_app.config.get('CORS_DOMAINS'):
                    response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
            for h in to_add:
                response.headers.add(*h)
            return response
        return f

    return decorator


def on_adsws_error(e):
    return jsonify(dict(error=e.msg)), 400


def on_adsws_form_error(e):
    return jsonify(dict(errors=e.errors)), 400


def on_404(e):
    return jsonify(dict(error='Not found')), 404

def on_401(e):
    return jsonify(dict(error='Unauthorized')), 401

def limit_rate(*scopes):
    """Protect resource with specified scopes."""
    def get_curr_rate(oauth):
        c = OAuthClientLimits.query.filter_by(client_id=oauth.client.client_id).first()
        if c is None:
            expires = datetime.utcnow() + timedelta(
                seconds=int(current_app.config.get(
                    'MAX_RATE_EXPIRES_IN',
                    3600
                )))
            
            c = OAuthClientLimits(client_id=oauth.client.client_id, expires=expires)
        return c
    
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):

            if hasattr(request, 'oauth') and request.oauth:
                # TODO: this is just a temporary solution
                limits = current_app.config.get('MAX_RATE_LIMITS', {'default': 100})
                max_rate = limits['default']
                if request.oauth.user.email in limits:
                    max_rate = limits[request.oauth.user.email]
                
                curr_rate = get_curr_rate(request.oauth)
                curr_rate.increase()
                
                if curr_rate.totals() >= max_rate:
                    abort(401)
                return f(*args, **kwargs)

            return abort(401)
        return decorated
    return wrapper