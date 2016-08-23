"""
Management commands for account related activities (including oauth)
"""

import datetime

from adsws.modules.oauth2server.models import OAuthToken, OAuthClient
from adsws.core.users import User
from adsws.core import db
from adsws.accounts import create_app
from sqlalchemy import or_, exc
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
def cleanup_users(app_override=None, timedelta="hours=24"):
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
            app.logger.info("Deleted unverified user: {}".format(user.email))
        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
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
            return
        app.logger.info("Deleted {0} oauth2clients whose last_activity was "
                        "at least {1} old".format(deletions, timedelta))


@accounts_manager.command
def update_scopes(app_override=None, old_scopes='', new_scopes='', 
                  force_token_update=False):
    """
    Updates scopes for both the clients and active tokens in the
    database defined in app.config['SQLALCHEMY_DATABASE_URI']
    :param app_override: flask.app instance to use instead of manager.app
    :param old_scopes: String representing the existing scopes, e.g.
            "user store-preferences"
    :type old_scopes: basestring
    :param new_scopes: String representing the desired scopes, e.g.
            "user store-preferences store-data"
    :type new_scopes: basestring
    :param force_token_update: Update any matching OauthToken even if
          cannot be traced to an existing OAuthClient
    :type force_token_update: boolean
    :return: None
    """

    app = accounts_manager.app if app_override is None else app_override

    if set(old_scopes.split()) == set(new_scopes.split()):
        app.logger.warn("Hmmm, useless scope replacement of {0) with {1}"
                        .format(old_scopes, new_scopes))
    
    orig_old_scopes = old_scopes
    old_scopes = set((old_scopes or '').split(' '))
    new_scopes = ' '.join(sorted((new_scopes or '').split(' ')))
    
    
    with app.app_context():
        # first find all oauth clients that would be affected by this
        # change (we could search the database to give us the clients,
        # but since this is a maintenance routine, we'll go through
        # them all and check their scopes manually)
        clients = db.session.query(OAuthClient).all()
        to_update = set()
        total = 0

        for client in clients:
            total += 1
            if old_scopes == set((client._default_scopes or '').split(' ')):
                to_update.add(client.client_id)
                db.session.begin_nested()
                try:
                    client._default_scopes = new_scopes
                    
                    # now update the existing tokens
                    total = 0
                    updated = 0
                    tokens = db.session.query(OAuthToken).filter_by(client_id=client.client_id).all()
                    for token in tokens:
                        if set((token._scopes or '').split(' ')) == old_scopes:
                            token._scopes = new_scopes
                            updated += 1
                        total += 1
                    db.session.commit()
                    
                    app.logger.info("Updated {0} oauth2tokens (out of total: {1}) for {2}"
                        .format(updated, total, client.client_id))
                except exc.IntegrityError, e:
                    db.session.rollback()
                    app.logger.error("Could not update scope of oauth2client: {0}. "
                                     "Database error; rolled back: {1}"
                                     .format(client.client_id, e))
        
        if force_token_update:
            tokens = db.session.query(OAuthToken).filter(or_(OAuthToken._scopes==orig_old_scopes, 
                                                                OAuthToken._scopes==' '.join(sorted(list(old_scopes))))).all()
            for token in tokens:
                db.session.begin_nested()
                try:
                    token._scopes = new_scopes
                    db.session.commit()
                except exc.IntegrityError, e:
                    db.session.rollback()
                    app.logger.error("Could not update scope of oauth2token: {0}. "
                                     "Database error; rolled back: {1}"
                                     .format(token.id, e))
    
                 
        app.logger.info("Updated {0} oauth2clients (out of total: {1})"
                        .format(len(to_update), total))
        
        # per PEP-0249 a transaction is always in progress    
        db.session.commit()
