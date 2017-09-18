"""
Utility functions for adsws.ext.ratelimiter
"""

from flask import request, current_app
from flask.ext.login import current_user
from flask_limiter.util import get_remote_address
from flask_limiter.util import get_ipaddr

def key_func():
    """
    Returns the key with which to track the endpoint's requests
    for the purposes of ratelimiting
    """
    return get_ipaddr() # uses the last ip address in the X-Forwarded-For header, else falls back to the remote_address of the request
    #return get_remote_address()
    #return request.endpoint

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
        return request.remote_addr


def limit_func(counts, per_second):
    """
    Returns the default limit multiplied by user's ratelimit_level attribute,
    if it exists.
    :param counts: default rate limit
    :type counts: int
    :param per_second: time span in seconds
    :type counts: int
    :return user's ratelimit
    :rtype int
    """
    factor = 1
    if hasattr(request, 'oauth'):
        try:
            factor = request.oauth.user.ratelimit_level or 1
        except AttributeError:
            pass
    return "{0}/{1} second".format(counts * factor, per_second)
