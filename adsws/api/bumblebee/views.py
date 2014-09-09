from flask_login import current_user

from flask import Blueprint, request, session
from flask import current_app

from .. import route

from adsws.modules.oauth2server.provider import oauth2

blueprint = Blueprint('bumblebee', __name__)

@route(blueprint, '/bootstrap', methods=['GET'])
def bootstrap():
    """Returns the datastruct necessary for Bumblebee bootstrap."""
    
    out = {}
    
    if current_user.is_authenticated():
    