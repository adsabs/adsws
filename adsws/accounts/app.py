from ..core import AdsWSError, AdsWSFormError, JSONEncoder
from .. import factory

from flask_restful import Api
from flask_cors import CORS
from flask_wtf.csrf import CsrfProtect
from flask_mail import Mail
from flask import jsonify, abort
from itsdangerous import URLSafeTimedSerializer

from .views import \
    UserAuthView, LogoutView, UserRegistrationView, \
    VerifyEmailView, ChangePasswordView, \
    PersonalTokenView, UserInfoView, Bootstrap, StatusView, OAuthProtectedView, \
    ForgotPasswordView, ChangeEmailView, DeleteAccountView, CSRFView

def create_app(**kwargs_config):
    """
    Create the flask app
    :param kwargs_config: overwrite any base level config
    :return: flask.Flask instance
    """

    app = factory.create_app(
        app_name=__name__.replace('.app', ''),
        **kwargs_config
    )

    api = Api(app)
    api.unauthorized = lambda noop: noop #Overwrite WWW-Authenticate challenge on 401

    csrf = CSRFProtect(app)

    mail = Mail(app)

    cors = CORS(app,
                origins=app.config.get('CORS_DOMAINS'),
                allow_headers=app.config.get('CORS_HEADERS'),
                methods=app.config.get('CORS_METHODS'),
                supports_credentials=True,
                )

    app.json_encoder = JSONEncoder
    api.add_resource(Bootstrap, '/bootstrap')
    api.add_resource(StatusView, '/status')
    api.add_resource(OAuthProtectedView, '/protected')
    api.add_resource(CSRFView, '/csrf')
    api.add_resource(UserAuthView, '/user')
    api.add_resource(DeleteAccountView, '/user/delete')
    api.add_resource(UserRegistrationView, '/register')
    api.add_resource(LogoutView, '/logout')
    api.add_resource(PersonalTokenView, '/token')
    api.add_resource(UserInfoView, '/info/<string:account_data>')
    api.add_resource(ChangePasswordView, '/change-password')
    api.add_resource(ChangeEmailView, '/change-email')
    api.add_resource(VerifyEmailView, '/verify/<string:token>')
    api.add_resource(ForgotPasswordView, '/reset-password/<string:token>')
    app.ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])

    @app.login_manager.unauthorized_handler
    def unauthorized():
        """
        flask_login callback when @login_required is not met.
        This overrides the default behavior or re-directing to a login view
        """
        abort(401)

    # Register custom error handlers
    if not app.config.get('DEBUG'):
        app.errorhandler(AdsWSError)(on_adsws_error)
        app.errorhandler(AdsWSFormError)(on_adsws_form_error)

        @app.errorhandler(CSRFError)
        def csrf_error(reason):
            app.logger.warning("CSRF Blocked: {reason}".format(reason=reason))
            return jsonify(dict(error="Invalid CSRF token")), 400
    return app


def on_adsws_error(e):
    return jsonify(dict(error=e.msg)), 400


def on_adsws_form_error(e):
    return jsonify(dict(errors=e.errors)), 400
