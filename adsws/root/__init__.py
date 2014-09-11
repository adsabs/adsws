from adsws import factory

def create_app(**kwargs_config):
    """Returns the AdsWS API application instance"""

    app = factory.create_app(app_name=__name__, **kwargs_config)

    return app