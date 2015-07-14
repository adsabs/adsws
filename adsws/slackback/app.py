"""
Application factory
"""

from .. import factory
from flask.ext.restful import Api
from adsws.slackback.views import SlackFeedback

def create_app(**kwargs_config):
    """
    Create the flask app
    :param kwargs_config: overwrite any base level config
    :return: flask.Flask instance
    """

    app = factory.create_app(
        app_name=__name__.replace('.app', ''),
        **kwargs_config
    )

    # Load config and logging

    # Register extensions
    api = Api(app)

    # Add end points
    api.add_resource(SlackFeedback, '/slack')

    return app