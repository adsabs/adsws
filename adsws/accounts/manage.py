"""
Management commands for account related activities (including oauth)
"""

import datetime

from adsws.modules.oauth2server.models import OAuthToken, OAuthClient
from adsws.core.users import User
from adsws.core import db
from adsws.accounts import create_app

from flask.ext.script import Manager

accounts_manager = Manager(create_app())
accounts_manager.__doc__ = __doc__  # Overwrite default docstring


def parse_timedelta(s):
    """
    Helper function which converts a string formatted timedelta into a
    datetime.timedelta object

    :param s: string formatted timedelta (e.g. "days=1")
    :return: parsed timedelta
    :rtype: datetime.timedelta
    """

    td = {s.split('=')[0]: float(s.split('=')[1])}
    return datetime.timedelta(**td)

@accounts_manager.command
def cleanup_users(app_override=None, timedelta="hours=2"):
    """
    Deletes stale users from the database. Stale users are defined as users
    that have a registered_at value of `now`-`timedelta` but not confirmed_at
    value

    This is expected to coorespond to users that created an account but never
    verified it.

    :param app_override: flask.app instance to use instead of manager.app
    :param timedelta: String representing the datetime.timedelta against which
            to compare user's registered_at ["hours=24"].
    :return: None
    """

    app = accounts_manager.app if app_override is None else app_override

    td = parse_timedelta(timedelta)

    with app.app_context():
        users = db.session.query(User).filter(
            User.registered_at <= datetime.datetime.now()-td,
            User.confirmed_at == None,
        )

        deletions = 0

        for user in users:
            db.session.delete(user)
            deletions += 1
        try:
            db.session.commit()
        except Exception, e:
            app.logger.error("Could not cleanup stale users. "
                             "Database error; rolled back: {0}".format(e))
        app.logger.info("Deleted {0} stale users".format(deletions))


@accounts_manager.command
def cleanup_tokens(app_override=None):
    """
    Cleans expired oauth2tokens from the database defined in
    app.config['SQLALCHEMY_DATABASE_URI']
    :param app_override: flask.app instance to use instead of manager.app
    :return: None
    """

    app = accounts_manager.app if app_override is None else app_override

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


@accounts_manager.command
def cleanup_clients(app_override=None, timedelta="days=31"):
    """
    Cleans expired oauth2clients that are older than a specified date in the
    database defined in app.config['SQLALCHEMY_DATABASE_URI']
    :param app_override: flask.app instance to use instead of manager.app
    :param timedelta: String representing the datetime.timedelta against which
            to compare client's last_activity ["days=31"].
    :type timedelta: basestring
    :return: None
    """

    app = accounts_manager.app if app_override is None else app_override

    td = parse_timedelta(timedelta)

    with app.app_context():
        clients = db.session.query(OAuthClient).filter(
            OAuthClient.last_activity <= datetime.datetime.now()-td
        ).all()
        deletions = 0

        for client in clients:
            db.session.delete(client)
            deletions += 1
        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
            app.logger.error("Could not cleanup expired oauth2clients. "
                             "Database error; rolled back: {0}".format(e))
        app.logger.info("Deleted {0} oauth2clients whose last_activity was "
                        "at least {1} old".format(deletions, timedelta))


