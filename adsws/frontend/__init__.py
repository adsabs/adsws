# -*- coding: utf-8 -*-
"""
    adsws.frontend
    ~~~~~~~~~~~~~~~~~~

    launchpad frontend application package
"""

from functools import wraps

from flask import render_template
from flask_security import login_required

from .. import factory
from . import assets


def create_app(**kwargs_config):
    """Returns the AdsWS dashboard application instance"""
    if 'EXTENSIONS' in kwargs_config:
        kwargs_config['EXTENSIONS'].append('adsws.ext.sqlalchemy')
        kwargs_config['EXTENSIONS'].append('adsws.ext.mail')
        kwargs_config['EXTENSIONS'].append('adsws.ext.security')
        kwargs_config['PACKAGES'].append('adsws.frontend')
    else:
        kwargs_config['EXTENSIONS'] = ['adsws.ext.sqlalchemy', 'adsws.ext.mail', 'adsws.ext.security']
        kwargs_config['PACKAGES'] = ['adsws.frontend']
        
    app = factory.create_app(__name__, **kwargs_config)

    return app



def route(bp, *args, **kwargs):
    def decorator(f):
        @bp.route(*args, **kwargs)
        @login_required
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return f

    return decorator
