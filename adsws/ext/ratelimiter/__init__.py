"""
Centralized location for configuring ratelimiting for the adsws
"""

from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .utils import limit_func, scope_func, key_func

class ADSLimiter(Limiter):

    def __init__(self, *args, **kwargs):
        super(ADSLimiter, self).__init__(*args, **kwargs)

    def forget(self):
        """
        Forget any previous route.
        """
        self._exempt_routes = set()
        self._request_filters = []
        self._header_mapping = {}
        self._route_limits = {}
        self._dynamic_route_limits = {}
        self._blueprint_limits = {}
        self._blueprint_dynamic_limits = {}
        self._blueprint_exempt = set()

    def limit_and_check(self, *args, **kwargs):
        kwargs.update({'shared': False})
        return self._limit_and_check(*args, **kwargs)

    def shared_limit_and_check(self, *args, **kwargs):
        kwargs.update({'shared': True})
        return self._limit_and_check(*args, **kwargs)

    def _limit_and_check(self, *args, **kwargs):
        """
        auto_check should be False or Flask Limiter 0.9.5.1 will be run before OAuth
        plugin, but then this method should be used as decorator to trigger
        the actual check when the requests is treated.

        https://github.com/alisaifee/flask-limiter/issues/67
        """
        kwargs.setdefault('key_func', None)
        kwargs.setdefault('shared', False)
        kwargs.setdefault('scope', None)
        kwargs.setdefault('per_method', True)
        kwargs.setdefault('methods', None)
        kwargs.setdefault('error_message', None)
        kwargs.setdefault('exempt_when', None)
        def inner(func):
            # register for check
            self._Limiter__limit_decorator(*args, **kwargs)(func)

            @wraps(func)
            def check(*args, **kwargs):
                self.check()  # actually do the check
                return func(*args, **kwargs)

            return check

        return inner


# [hack]
# auto_check should be False or Flask Limiter 0.9.5.1 will be run before OAuth plugin
# https://github.com/alisaifee/flask-limiter/issues/67
# [/hack]
ratelimit = ADSLimiter(auto_check=False)


def setup_app(app):
    """
    Run at application registry
    :param app: flask application instance
    :return: extension-registered app instance
    """
    # [hack]
    # When testing, an app is created for every single test but the limiter is
    # always the same. We make sure that the new app forgets about routes and
    # limits set with the previous app instance (or limit registration will be
    # triggered more than once)
    ratelimit.forget()
    # [/hack]
    # [hack] until this Flask-Ratelimit 0.9.5.1 bug is fixed:
    #   https://github.com/alisaifee/flask-limiter/issues/88
    if 'RATELIMIT_KEY_PREFIX' in app.config:
        ratelimit._key_prefix = app.config['RATELIMIT_KEY_PREFIX']
    # [/hack]
    ratelimit.init_app(app)
    return app
