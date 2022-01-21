"""
Application factory
"""

from .. import factory
from flask_restful import Api
from flask_cors import CORS
from adsws.feedback.views import UserFeedback
from flask_mail import Mail


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
    mail = Mail(app)
    CORS(
        app,
        origins=app.config.get('CORS_DOMAINS'),
        allow_headers=app.config.get('CORS_HEADERS'),
        methods=app.config.get('CORS_METHODS'),
        supports_credentials=True,
    )

    # Add end points
    api.add_resource(UserFeedback, '/userfeedback')
    

    return app
