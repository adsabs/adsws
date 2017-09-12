"""
Centralized location for configuring ratelimiting for the adsws
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .utils import scope_func, limit_func

ratelimit = Limiter()


def setup_app(app):
    """
    Run at application registry
    :param app: flask application instance
    :return: extension-registered app instance
    """
    ratelimit.init_app(app)
    return app
