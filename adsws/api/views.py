from adsws.modules.oauth2server.provider import oauth2
from flask.ext.restful import Resource
from flask import current_app, request

class ProtectedView(Resource):
    """This view is oauth2-authentication protected"""
    decorators = [oauth2.require_oauth()]
    def get(self):
        return {
            'app': current_app.name,
            'user': request.oauth.user.email
        }, 200


class StatusView(Resource):
    """Returns the status of this app"""
    def get(self):
        return {
            'app': current_app.name,
            'status': 'online'
        }, 200