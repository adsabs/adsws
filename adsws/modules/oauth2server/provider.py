# -*- coding: utf-8 -*-

"""
Configuration of authlib provider
"""

from authlib.integrations.flask_oauth2 import AuthorizationServer
from datetime import datetime, timedelta

from flask import current_app, request
from flask_login import current_user
from flask_oauthlib.provider import OAuth2Provider
from flask_oauthlib.utils import extract_params
from flask_login import current_user

from adsws.core import db, user_manipulator
from .models import OAuthToken, OAuthClient, OAuthGrant
from functools import wraps

class OAuth2bProvider(OAuth2Provider):
    def optional_oauth(self, *scopes):
        """Protect resource with specified scopes."""
        def wrapper(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                for func in self._before_request_funcs:
                    func()

                if hasattr(request, 'oauth') and request.oauth:
                    return f(*args, **kwargs)

                server = self.server
                uri, http_method, body, headers = extract_params()
                valid, req = server.verify_request(
                    uri, http_method, body, headers, scopes
                )

                for func in self._after_request_funcs:
                    valid, req = func(valid, req)

                if valid:
                    request.oauth = req
                return f(*args, **kwargs)
            return decorated
        return wrapper

oauth2_provider = OAuth2bProvider()

authlib_provider = AuthorizationServer()

@oauth2_provider.clientgetter
def load_client(client_id):
    """
    Loads the client that is sending the requests.
    """
    return OAuthClient.query.filter_by(client_id=client_id).first()

@oauth2_provider.grantgetter
def load_grant(client_id, code):
    """
    Grant is a temporary token (a ticket to 'access_token').
    """
    return OAuthGrant.query.filter_by(client_id=client_id, code=code).first()

@oauth2_provider.grantsetter
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

@oauth2_provider.usergetter
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


@oauth2_provider.tokengetter
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


@oauth2_provider.tokensetter
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

    # scopes are sorted alphabetically before writing to a database
    # this makes administrative tasks easier
    tok = OAuthToken(
        access_token=token['access_token'],
        refresh_token=token.get('refresh_token'),
        token_type=token['token_type'],
        _scopes=' '.join(sorted((token['scope'] or '').split(' '))),
        expires=expires,
        client_id=request.client.client_id,
        user_id=uid,
        is_personal=False,
    )
    db.session.add(tok)
    db.session.commit()
    return tok
