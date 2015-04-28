"""
Centralized location for configuring ratelimiting for the adsws
"""

from flask.ext.ratelimiter import RateLimiter, ratelimit

ratelimiter = RateLimiter()

def setup_app(app):
    """
    Run at application registry
    :param app: flask application instance
    :return: extension-registered app instance
    """
    ratelimiter.init_app(app)
    return app