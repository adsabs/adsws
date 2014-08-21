# -*- coding: utf-8 -*-
"""
    adsws.api
    ~~~~~~~~~~~~~

    adsws api application package
"""

from functools import wraps

from flask import jsonify
from flask_security import login_required

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

    return app


def route(bp, *args, **kwargs):
    kwargs.setdefault('strict_slashes', False)

    def decorator(f):
        @bp.route(*args, **kwargs)
        #@login_required
        @wraps(f)
        def wrapper(*args, **kwargs):
            sc = 200
            rv = f(*args, **kwargs)
            if isinstance(rv, tuple):
                sc = rv[1]
                rv = rv[0]
            if isinstance(rv, basestring):
                return rv, sc # assuming it is a json string
            elif isinstance(rv, dict):
                return jsonify(rv), sc
            else:
                return jsonify(dict(data=rv)), sc
        return f

    return decorator


def on_adsws_error(e):
    return jsonify(dict(error=e.msg)), 400


def on_adsws_form_error(e):
    return jsonify(dict(errors=e.errors)), 400


def on_404(e):
    return jsonify(dict(error='Not found')), 404
