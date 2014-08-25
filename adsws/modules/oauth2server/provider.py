# -*- coding: utf-8 -*-

"""
Configuration of flask-oauthlib provider
"""

from datetime import datetime, timedelta

from flask import current_app
from flask.ext.login import current_user
from flask_oauthlib.provider import OAuth2Provider
from flask_login import current_user

from adsws.core import db, user_manipulator
from .models import OAuthToken, OAuthClient, OAuthGrant


oauth2 = OAuth2Provider()

@oauth2.clientgetter
def load_client(client_id):
    """
    Loads the client that is sending the requests.
    """
    return OAuthClient.query.filter_by(client_id=client_id).first()

@oauth2.grantgetter
def load_grant(client_id, code):
    """
    Grant is a temporary token (a ticket to 'access_token').
    """
    return OAuthGrant.query.filter_by(client_id=client_id, code=code).first()

@oauth2.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    """
    Method to create/save grant token - it is bound to the
    user that initialized the request.
    """
    uid = request.user.id if request.user else current_user.get_id()
    
    expires = datetime.utcnow() + timedelta(
                seconds=int(current_app.config.get(
                    'OAUTH2_PROVIDER_GRANT_EXPIRES_IN',
                    100
                )))
    grant = OAuthGrant(
        client_id=client_id,
        code=code['code'],
        redirect_uri=request.redirect_uri,
        _scopes=' '.join(request.scopes),
        user_id=uid,
        expires=expires
    )
    db.session.add(grant)
    db.session.commit()
    return grant

@oauth2.usergetter
def load_user(username, password, *args, **kwargs):
    """
    Loads the user (resource owner)
    
    User getter is optional. It is only required if you need password 
    credential authorization:
    
    Needed for grant type 'password'. Note, grant type password is by default
    disabled.
    """
    user = user_manipulator.first(email=username)
    if user.validate_password(password):
        return user


@oauth2.tokengetter
def load_token(access_token=None, refresh_token=None):
    """
    Load an access token

    Add support for personal access tokens compared to flask-oauthlib
    """
    if access_token:
        t = OAuthToken.query.filter_by(access_token=access_token).first()
        if t and t.is_personal:
            t.expires = datetime.utcnow() + timedelta(
                seconds=int(current_app.config.get(
                    'OAUTH2_PROVIDER_TOKEN_EXPIRES_IN',
                    3600
                ))
            )
        return t
    elif refresh_token:
        return OAuthToken.query.filter_by(
            refresh_token=refresh_token, is_personal=False,
            ).first()
    else:
        return None


@oauth2.tokensetter
def save_token(token, request, *args, **kwargs):
    """
    Token persistence
    """
    uid = request.user.id if request.user else current_user.get_id()
    # Exclude the personal access tokens which doesn't expire.
    tokens = OAuthToken.query.filter_by(
        client_id=request.client.client_id,
        user_id=uid,
        is_personal=False,
    )

    # make sure that every client has only one token connected to a user
    if tokens:
        for tk in tokens:
            db.session.delete(tk)
        db.session.commit()

    expires_in = token.pop('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=int(expires_in))

    tok = OAuthToken(
        access_token=token['access_token'],
        refresh_token=token.get('refresh_token'),
        token_type=token['token_type'],
        _scopes=token['scope'],
        expires=expires,
        client_id=request.client.client_id,
        user_id=uid,
        is_personal=False,
    )
    db.session.add(tok)
    db.session.commit()
    return tok
