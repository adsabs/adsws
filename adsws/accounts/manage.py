"""
Management commands for account related activities (including oauth)
"""

import datetime

from adsws.modules.oauth2server.models import OAuthToken
from adsws.core import db
from adsws.accounts import create_app

from flask.ext.script import Manager, Command

_app = create_app()
accounts_manager = Manager(_app)
accounts_manager.__doc__ = __doc__  # Overwrite default docstring


@accounts_manager.command
def cleanup_tokens(app=_app):
    """
    Cleans expired oauth2tokens from the database defined in
    app.config['SQLALCHEMY_DATABASE_URI']
    :param app: Flask application to bind on
    :return: None
    """

    with app.app_context():
        tokens = db.session.query(OAuthToken).filter(
            OAuthToken.expires <= datetime.datetime.now()
        ).all()
        deletions = 0

        for token in tokens:
            db.session.delete(token)
            deletions += 1
        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
            app.logger.error("Could not cleanup expired oauth2tokens. "
                             "Database error; rolled back: {0}".format(e))
        app.logger.info("Deleted {0} expired oauth2tokens".format(deletions))



