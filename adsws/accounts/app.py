from ..core import AdsWSError, AdsWSFormError, JSONEncoder
from .. import factory

from flask.ext.ratelimiter import RateLimiter
from flask.ext.restful import Api
from flask.ext.cors import CORS
from flask.ext.wtf.csrf import CsrfProtect
from flask.ext.mail import Mail
from flask import jsonify
from itsdangerous import URLSafeTimedSerializer

from views import (
  UserAuthView, LogoutView, UserRegistrationView,
  VerifyEmailView,ChangePasswordView,
  PersonalTokenView, Bootstrap, StatusView, ProtectedView,
  ForgotPasswordView, ChangeEmailView, DeleteAccountView
  )

def create_app(**kwargs_config):
  app = factory.create_app(app_name=__name__.replace('.app',''), **kwargs_config)

  api = Api(app)
  api.unauthorized = lambda noop: noop #Overwrite WWW-Authenticate challenge on 401

  ratelimiter = RateLimiter(app=app)

  csrf = CsrfProtect(app)  

  mail = Mail(app)
  
  cors = CORS(app,origins=app.config.get('CORS_DOMAINS'), allow_headers=app.config.get('CORS_HEADERS'),methods=app.config.get('CORS_METHODS'))

  app.json_encoder = JSONEncoder
  api.add_resource(Bootstrap,'/bootstrap')
  api.add_resource(StatusView,'/status')
  api.add_resource(ProtectedView,'/protected')
  api.add_resource(UserAuthView,'/user')
  api.add_resource(DeleteAccountView,'/user/delete')
  api.add_resource(UserRegistrationView,'/register')
  api.add_resource(LogoutView,'/logout')
  api.add_resource(PersonalTokenView,'/token')
  api.add_resource(ChangePasswordView,'/change-password')
  api.add_resource(ChangeEmailView,'/change-email')
  api.add_resource(VerifyEmailView,'/verify/<string:token>')
  api.add_resource(ForgotPasswordView,'/reset-password/<string:token>')
  app.ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])

  # Register custom error handlers
  if not app.config.get('DEBUG'):
    app.errorhandler(AdsWSError)(on_adsws_error)
    app.errorhandler(AdsWSFormError)(on_adsws_form_error)
    app.errorhandler(404)(on_404)
    app.errorhandler(401)(on_401)
    @csrf.error_handler
    def csrf_error(reason):
      app.logger.warning("CSRF Blocked: {reason}".format(reason=reason))
      return jsonify(dict(error="Invalid CSRF token")), 400
  return app

def on_adsws_error(e):
  return jsonify(dict(error=e.msg)), 400

def on_adsws_form_error(e):
  return jsonify(dict(errors=e.errors)), 400

def on_404(e):
  return jsonify(dict(error='Not found')), 404

def on_401(e):
  return jsonify(dict(error='Unauthorized')), 401
