"""
Utility functions for adsws.ext.ratelimiter
"""

from flask import request


def scope_func():
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
    # If request doesn't have oauth-identifying information, fall back to
    # the request's IP address.
    else:
        return request.remote_addr


def limit_func(default):
    """
    Returns the default limit multiplied by user's ratelimit_level attribute,
    if it exists.
    :param default: default rate limit
    :type default: int
    :return user's ratelimit
    :rtype int
    """
    factor = 1
    try:
        factor = request.oauth.user.ratelimit_level or 1
    except AttributeError:
        pass
    return default * factor
