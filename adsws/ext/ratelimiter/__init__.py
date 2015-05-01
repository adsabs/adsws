"""
Centralized location for configuring ratelimiting for the adsws
"""

from flask.ext.ratelimiter import RateLimiter, ratelimit
from .utils import scope_func, limit_func

_ratelimiter = RateLimiter()


def setup_app(app):
    """
    Run at application registry
    :param app: flask application instance
    :return: extension-registered app instance
    """
    _ratelimiter.init_app(app)
    return app