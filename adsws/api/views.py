from flask import Blueprint, request
from flask import current_app

from . import route

from adsws.modules.oauth2server.provider import oauth2

blueprint = Blueprint('api', __name__)

@route(blueprint, '/info', methods=['GET'])
@oauth2.require_oauth()
def search():
    """Returns info when you can access the api."""
    
    return "You are accessing API version '%s' as user '%s'." % (
                        current_app.config['VERSION'],
                        request.oauth.user.email
                        )

