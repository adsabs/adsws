from adsws.modules.oauth2server.provider import oauth2
from flask_restful import Resource
from adsws.core import user_manipulator
from flask import current_app, request, abort


class ProtectedView(Resource):
    """
    This view is oauth2-authentication protected
    """
    decorators = [oauth2.require_oauth()]
    def get(self):
        return {
            'app': current_app.name,
            'user': request.oauth.user.email
        }, 200


class StatusView(Resource):
    """
    Returns the status of this app
    """
    def get(self):
        return {
            'app': current_app.name,
            'status': 'online'
        }, 200


class UserResolver(Resource):
    """
    Resolves an email or uid into a string formatted user object
    """

    decorators = [oauth2.require_oauth('adsws:internal')]

    def get(self, identifier):
        """
        :param identifier: email address or uid
        :return: json containing user info or 404
        """

        try:
            u = user_manipulator.get(int(identifier))
        except ValueError:
            u = user_manipulator.find(email=identifier).first()

        if u is None:
            abort(404)

        return {
            "id": u.id,
            "email": u.email,
        }