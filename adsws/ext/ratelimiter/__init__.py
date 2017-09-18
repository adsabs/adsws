"""
Centralized location for configuring ratelimiting for the adsws
"""

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


ratelimit = ADSLimiter()


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
