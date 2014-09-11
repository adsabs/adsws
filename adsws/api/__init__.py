# -*- coding: utf-8 -*-
"""
    adsws.api
    ~~~~~~~~~~~~~

    adsws api application package
"""

from functools import wraps

from flask import jsonify, current_app, Response, make_response,\
    request

from ..core import AdsWSError, AdsWSFormError, JSONEncoder
from .. import factory


def create_app(**kwargs_config):
    """Returns the AdsWS API application instance"""

    app = factory.create_app(app_name=__name__, **kwargs_config)

    # Set the default JSON encoder
    app.json_encoder = JSONEncoder

    # Register custom error handlers
    if not app.config.get('DEBUG', False):
        app.errorhandler(AdsWSError)(on_adsws_error)
        app.errorhandler(AdsWSFormError)(on_adsws_form_error)
        app.errorhandler(404)(on_404)

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
                # Chrome/Webkit wants this
                to_add.append(("Access-Control-Allow-Headers", "Content-Type"))
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
