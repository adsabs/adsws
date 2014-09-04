# -*- coding: utf-8 -*-
"""
    adsws.frontend
    ~~~~~~~~~~~~~~~~~~

    launchpad frontend application package
"""

from .. import factory

def create_app(**kwargs_config):
    """Returns the AdsWS dashboard application instance"""
        
    app = factory.create_app(__name__, **kwargs_config)

    return app

