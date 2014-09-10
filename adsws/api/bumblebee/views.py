from datetime import datetime, timedelta

from flask_login import current_user, login_user

from flask import Blueprint, request, session
from flask import current_app, session
from werkzeug.security import gen_salt

from .. import route
from adsws.core import db, user_manipulator

from adsws.modules.oauth2server.provider import oauth2
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken

blueprint = Blueprint('api_bumblebee', __name__)

@route(blueprint, '/bootstrap', methods=['GET'])
def bootstrap():
    """Returns the datastruct necessary for Bumblebee bootstrap."""
    
    scopes = current_app.config.get('API_BUMBLEBEE_BOOTSTRAP_DEFAULT_SCOPES', 
                                                              " ".join(['api:search'
                                                               ])
    
    if not current_user.is_authenticated():
        login_user(user_manipulator.get(current_app.config.get('ANONYMOUS_USER', 'anonymous@adslabs.org')), 
                   remember=False, force=True)
    
    client = None
    if '_oauth_client' in session:
        client = OAuthClient.query.filter_by(
                client_id=session['_oauth_client'],
                user_id=current_user.get_id(),
            ).first()
            
    if client is None:
        client = OAuthClient(user_id=current_user.get_id(),
                        name='Bumblebee UI client',
                        description='This client is created for any user that accesses ADS 2.0 interface',
                        website='http://adslabs.org/bumblebee',
                        is_confidential=False,
                        is_internal=True,
                        _redirect_uris=current_app.config.get('API_BUMBLEBEE_BOOTSTRAP_REDIRECT_URIS', 
                                                              "\n".join(['https://adslabs.org/bumblebee',
                                                               'http://adslabs.org/bumblebee',
                                                               'https://adslabs.org',
                                                               'http://adslabs.org'
                                                               ])),
                        _default_scopes=scopes
                        )
        client.gen_salt()
        
        db.session.add(client)
        db.session.commit()
        session['_oauth_client'] = client.client_id
    
    
    token = OAuthToken.query.filter_by(client_id=client.client_id, 
                                       user_id=current_user.get_id(),
                                       is_internal=True,
                                       is_confidential=False).first()
    if token is None:
        expires = datetime.utcnow() + timedelta(seconds=int(
                            current_app.config.get('API_BUMBLEBEE_BOOTSTRAP_EXPIRES_IN', 3600*24)))
        token = OAuthToken(
            client_id=client.client_id,
            user_id=current_user.get_id(),
            access_token=gen_salt(
                current_app.config.get('OAUTH2_TOKEN_PERSONAL_SALT_LEN', 40)
            ),
            refresh_token=gen_salt(
                current_app.config.get('OAUTH2_TOKEN_PERSONAL_SALT_LEN', 40)
            ),
            expires=None,
            _scopes=scopes,
            is_personal=False,
            is_internal=True,
        )

        db.session.add(token)
        db.session.commit()
        
    return {
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'username': current_user.email,
            }