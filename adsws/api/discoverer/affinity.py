import Cookie
from flask import request
from functools import wraps
from werkzeug.datastructures import Headers
from werkzeug.datastructures import ImmutableTypeConversionDict

def _get_solr_route(storage, solr_route_redis_prefix, user_token):
    """
    Obtains the solr route from redis for a given user token. It piggybacks the
    existing rate limiter extension connection, and if it fails the request
    will not be stopped (answering a request has a higher priority than
    assigning a solr instance).
    """
    try:
        solr_route = storage.get(solr_route_redis_prefix+user_token)
    except:
        solr_route = None
    return solr_route

def _set_solr_route(storage, solr_route_redis_prefix, user_token, solr_route, solr_route_redis_expiration_time):
    """
    Sets the solr route from redis for a given user token. It piggybacks the
    existing rate limiter extension connection, and if it fails the request
    will not be stopped (answering a request has a higher priority than
    assigning a solr instance).

    Keys in redis will expire in N seconds to reduce chances of saturation
    of a particular solr and to automatically clear entries in redis.
    """
    try:
        storage.setex(solr_route_redis_prefix+user_token, solr_route, solr_route_redis_expiration_time)
    except:
        pass

def _build_updated_cookies(request, user_token, solr_route, solr_route_cookie_name):
    """
    Based on the current request, create updated headers and cookies content
    attributes.
    """
    # Interpret cookie header content
    cookies_header = Cookie.SimpleCookie()
    currrent_cookie_content = request.headers.get('cookie', None)
    if currrent_cookie_content:
        cookies_header.load(currrent_cookie_content.encode("utf8"))
    # Interpret cookies attribute (immutable dict) as a normal dict
    if request.cookies:
        cookies = dict(request.cookies)
    else:
        cookies = {}
    # Update cookie structures
    if solr_route:
        # Create/update solr route
        cookies_header[solr_route_cookie_name] = solr_route.encode("utf8")
        cookies[solr_route_cookie_name] = solr_route
    else:
        # Discard non-registered solr route if it is present
        cookies_header.pop(solr_route_cookie_name, None)
        cookies.pop(solr_route_cookie_name, None)
    # Transform cookies structures into the format that request requires
    cookies_header_content = cookies_header.output(header="", sep=";")
    cookies_content = ImmutableTypeConversionDict(cookies)
    return cookies_header_content, cookies_content

def solr_route(storage, solr_route_cookie_name="sroute", solr_route_redis_prefix="token:sroute:", solr_route_redis_expiration_time=86400):
    """
    Assign a cookie that will be used by solr ingress to send request to
    a specific solr instance for the same user, maximizing the use of solr
    cache capabilities.

    The storage should be a redis connection.
    """

    def real_solr_route_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtain user token, giving priority to forwarded authorization field (used when a microservice uses its own token)
            user_token = request.headers.get('X-Forwarded-Authorization', None)
            if user_token is None:
                user_token = request.headers.get('Authorization', None)
            if user_token and len(user_token) > 7: # This should be always true
                user_token = user_token[7:] # Get rid of "Bearer:" or "Bearer "
                solr_route = _get_solr_route(storage, solr_route_redis_prefix, user_token)
                cookies_header_content, cookies_content = _build_updated_cookies(request, user_token, solr_route, solr_route_cookie_name)
                # Update request cookies (header and cookies attributes)
                request.headers = Headers(request.headers)
                request.headers.set('cookie', cookies_header_content)
                request.cookies = cookies_content

            r = f(*args, **kwargs)
            if type(r) is tuple and len(r) > 2:
                response_headers = r[2]
            elif hasattr(r, 'headers'):
                response_headers = r.headers
            else:
                response_headers = None

            if user_token and response_headers:
                set_cookie = response_headers.get('Set-Cookie', None)
                if set_cookie:
                    # If solr issued a set cookie, store the value in redis linked to the user token
                    cookie = Cookie.SimpleCookie()
                    cookie.load(set_cookie.encode("utf8"))
                    solr_route = cookie.get(solr_route_cookie_name, None)
                    if solr_route:
                        _set_solr_route(storage, solr_route_redis_prefix, user_token, solr_route.value, solr_route_redis_expiration_time)
            return r
        return decorated_function
    return real_solr_route_decorator

