# -*- coding: utf-8 -*-

"""
OAuth 2.0 Provider
"""

from __future__ import absolute_import

from flask import Blueprint, current_app, request, render_template, jsonify, \
    abort, session
from flask_oauthlib.contrib.oauth2 import bind_cache_grant, bind_sqlalchemy
from flask.ext.login import login_required

from invenio.ext.sqlalchemy import db
from invenio.ext.login import login_user

from ..provider import oauth2
from ..models import Client, OAuthUserProxy
from ..registry import scopes


blueprint = Blueprint(
    'oauth2server',
    __name__,
    url_prefix='/oauth',
    static_folder="../static",
    template_folder="../templates",
)


@blueprint.before_app_first_request
def setup_app():
    """
    Setup OAuth2 provider
    """
    # Initialize OAuth2 provider
    oauth2.init_app(current_app)

    # Register default scopes (note, each module will)
    for scope, options in current_app.config['OAUTH2_DEFAULT_SCOPES'].items():
        if scope not in scopes:
            scopes.register(scope, options)

    # Configures the OAuth2 provider to use the SQLALchemy models for getters
    # and setters for user, client and tokens.
    bind_sqlalchemy(oauth2, db.session, client=Client)

    # Configures an OAuth2Provider instance to use configured caching system
    # to get and set the grant token.
    bind_cache_grant(current_app, oauth2, OAuthUserProxy.get_current_user)


@oauth2.after_request
def login_oauth2_user(valid, oauth):
    """
    Login a user after having been verified
    """
    if valid:
        login_user(oauth.user.id)
    return valid, oauth


#
# Views
#
@blueprint.route('/authorize', methods=['GET', 'POST'])
@login_required
@oauth2.authorize_handler
def authorize(*args, **kwargs):
    """
    View for rendering authorization request.
    """
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['client'] = client
        return render_template('oauth2server/authorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'


@blueprint.route('/token', methods=['POST', ])
@oauth2.token_handler
def access_token():
    """
    Token view handles exchange/refresh access tokens
    """
    return None


@blueprint.route('/errors')
def errors():
    """
    Error view in case of invalid oauth requests
    """
    return render_template('oauth2server/errors.html')


@blueprint.route('/ping/')
@oauth2.require_oauth()
def ping(oauth_request):
    """
    Test to verify that you have been authenticated.
    """
    return jsonify(dict(ping="pong"))


@blueprint.route('/info/')
@oauth2.require_oauth('user')
def info(oauth_request):
    """
    Test to verify that you have been authenticated.
    """
    if current_app.testing or current_app.debug:
        return jsonify(dict(
            user=oauth_request.user.id,
            client=oauth_request.client.client_id,
            scopes=list(oauth_request.scopes),
        ))
    else:
        abort(404)


@blueprint.route('/invalid/')
@oauth2.require_oauth('invalid_scope')
def invalid(oauth_request):
    """
    Test to verify that you have been authenticated.
    """
    if current_app.testing or current_app.debug:
        # Not reachable
        return jsonify(dict(ding="dong"))
    else:
        abort(404)
