import Cookie
from flask import request, current_app
from functools import wraps
from werkzeug.datastructures import Headers
from werkzeug.datastructures import ImmutableTypeConversionDict

def _get_route(storage, route_redis_prefix, user_token):
    """
    Obtains the solr route from redis for a given user token. It piggybacks the
    existing rate limiter extension connection, and if it fails the request
    will not be stopped (answering a request has a higher priority than
    assigning a solr instance).
    """
    try:
        route = storage.get(route_redis_prefix+user_token)
        current_app.logger.info("Cached affinity route '{}'".format(route))
    except:
        route = None
    return route

def _set_route(storage, route_redis_prefix, user_token, route, route_redis_expiration_time):
    """
    Sets the solr route from redis for a given user token. It piggybacks the
    existing rate limiter extension connection, and if it fails the request
    will not be stopped (answering a request has a higher priority than
    assigning a solr instance).

    Keys in redis will expire in N seconds to reduce chances of saturation
    of a particular solr and to automatically clear entries in redis.
    """
    try:
        storage.setex(route_redis_prefix+user_token, route, route_redis_expiration_time)
        current_app.logger.info("Stored affinity route '{}'".format(route))
    except:
        pass

def _build_updated_cookies(request, user_token, route, name):
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
    if route:
        # Create/update solr route
        cookies_header[name] = route.encode("utf8")
        cookies[name] = route
    else:
        # Discard non-registered solr route if it is present
        cookies_header.pop(name, None)
        cookies.pop(name, None)
    # Transform cookies structures into the format that request requires
    cookies_header_content = cookies_header.output(header="", sep=";")
    cookies_content = ImmutableTypeConversionDict(cookies)
    return cookies_header_content, cookies_content

def affinity_decorator(storage, name="sroute"):
    """
    Assign a cookie that will be used by solr ingress to send request to
    a specific solr instance for the same user, maximizing the use of solr
    cache capabilities.

    The storage should be a redis connection.
    """
    route_redis_prefix="token:{}:".format(name)
    route_redis_expiration_time=86400 # 1 day

    def real_affinity_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtain user token, giving priority to forwarded authorization field (used when a microservice uses its own token)
            user_token = request.headers.get('X-Forwarded-Authorization', None)
            if user_token is None:
                user_token = request.headers.get('Authorization', None)
            if user_token and len(user_token) > 7: # This should be always true
                user_token = user_token[7:] # Get rid of "Bearer:" or "Bearer "
                route = _get_route(storage, route_redis_prefix, user_token)
                cookies_header_content, cookies_content = _build_updated_cookies(request, user_token, route, name)
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
                    route = cookie.get(name, None)
                    if route:
                        _set_route(storage, route_redis_prefix, user_token, route.value, route_redis_expiration_time)
            return r
        return decorated_function
    return real_affinity_decorator

