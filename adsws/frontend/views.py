from flask import current_app
from flask_login import current_user

from flask.ext.restful import Resource
from adsws.ext.ratelimiter import ratelimit, scope_func


class StatusView(Resource):

    def get(self):
        return {'app': current_app.name,
                'status': 'online',
                'user': current_user.is_authenticated() and current_user.email or 'anonymous'
                }, 200


class GlobalResourcesView(Resource):
    """
    Endpoint that exposes all of the resources that the adsws knows about.
    This endpoint, while public, is useful mostly for developers/debugging
    """
    decorators = [ratelimit.shared_limit_and_check("100/86400 second", scope=scope_func)]

    def get(self):
        return current_app.config['resources']
