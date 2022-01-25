"""
Utility functions for adsws.ext.ratelimiter
"""

from flask import request, current_app
from flask_login import current_user
from flask_limiter.util import get_remote_address


def key_func():
    """
    Returns the key with which to track the endpoint's requests
    for the purposes of ratelimiting
    """
    symbolic_ratelimits = current_app.extensions.get('symbolic_ratelimits', {})
    if request.endpoint in symbolic_ratelimits:
        return symbolic_ratelimits[request.endpoint]['key']
    return request.endpoint

def scope_func(endpoint_name):
    """
    Returns the key with which to track the user's requests
    for the purposes of ratelimiting
    """

    # If the request is oauth-authenticated, return email:client
    if hasattr(request, 'oauth') and request.oauth.client:
        return "{email}:{client}".format(
            email=request.oauth.user.email,
            client=request.oauth.client.client_id,
        )
    # Check if we have a user authenticated via a session cookie
    elif hasattr(current_user, 'email') and \
            'BOOTSTRAP_USER_EMAIL' in current_app.config and \
            current_user.email != current_app.config['BOOTSTRAP_USER_EMAIL']:
        return "{email}".format(email=current_user.email)
    # If request doesn't have oauth-identifying information, fall back to
    # the request's IP address.
    else:
        return get_remote_address()


def limit_func(counts, per_second):
    """
    Returns the default limit multiplied by the OAuth client's ratelimit attribute,
    if it exists.
    :param counts: default rate limit
    :type counts: int
    :param per_second: time span in seconds
    :type counts: int
    :return user's ratelimit
    :rtype int
    """
    
    symbolic_ratelimits = current_app.extensions.get('symbolic_ratelimits', {})
    
    if hasattr(request, 'oauth'):
        try:
            factor = request.oauth.client.ratelimit
            if factor is None:
                factor = 1.0
        except AttributeError:
            factor = 1.0
    else:
        factor = 1.0
    
    if request.endpoint in symbolic_ratelimits:
        counts = symbolic_ratelimits[request.endpoint]['count']
        per_second = symbolic_ratelimits[request.endpoint]['per_second']
        
    return "{0}/{1} second".format(int(counts * factor), per_second)
