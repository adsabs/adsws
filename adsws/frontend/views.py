from flask import current_app

from flask.ext.restful import Resource
from adsws.ext.ratelimiter import ratelimit, scope_func


class StatusView(Resource):
    decorators = [ratelimit(100, 24*60*60, scope_func=scope_func)]

    def get(self):
        return {'app': current_app.name, 'status': 'online'}, 200


class GlobalResourcesView(Resource):
    """
    Endpoint that exposes all of the resources that the adsws knows about.
    This endpoint, while public, is useful mostly for developers/debugging
    """
    decorators = [ratelimit(100, 24*60*60, scope_func=scope_func)]

    def get(self):
        return current_app.config['resources']
