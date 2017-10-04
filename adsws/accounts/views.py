import datetime
from werkzeug.security import gen_salt

from adsws.modules.oauth2server.models import OAuthClient, OAuthToken
from adsws.modules.oauth2server.provider import oauth2

from adsws.core import db, user_manipulator

from adsws.ext.ratelimiter import ratelimit, scope_func
from flask.ext.login import current_user, login_user
from flask.ext.restful import Resource, abort, reqparse
from flask.ext.wtf.csrf import generate_csrf
from flask import current_app, session, abort, request
from .utils import validate_email, validate_password, \
    verify_recaptcha, get_post_data, send_email, login_required, \
    print_token, logout_user
from .exceptions import ValidationError, NoClientError, NoTokenError
from .emails import PasswordResetEmail, VerificationEmail, \
    EmailChangedNotification


class StatusView(Resource):
    """
    Health check resource
    """
    def get(self):
        return {'app': current_app.name, 'status': 'online'}, 200


class OAuthProtectedView(Resource):
    """
    Resource for checking that oauth2.require_oauth is satisfied
    """
    decorators = [oauth2.require_oauth()]

    def get(self):
        return {'app': current_app.name, 'oauth': request.oauth.user.email}


class DeleteAccountView(Resource):
    """
    Implements the deletion of a adsws.core.users.models.User object
    """
    decorators = [login_required]

    def post(self):
        """
        Delete the current user's account
        use POST instead of GET to enable csrf validation
        """
        u = user_manipulator.first(email=current_user.email)
        logout_user()
        user_manipulator.delete(u)
        return {"message": "success"}, 200


class ForgotPasswordView(Resource):
    """
    Implements "reset password" functionality
    """
    def get(self, token):
        """
        Attempts to decode a verification token into an email.
        Responds with the resulting decoded email

        :param token: HMAC encoded string
        :type token: basestring
        """
        try:
            email = current_app.ts.loads(token,
                                         max_age=600,
                                         salt=PasswordResetEmail.salt)
        except:
            current_app.logger.warning(
                "Invalid Token {0} in ForgotPasswordView".format(token)
            )
            return {"error": "unknown verification token"}, 404

        # Check that the user still exists
        u = user_manipulator.first(email=email)
        if u is None:
            current_app.logger.error(
                "[GET] Reset password validated link,"
                " but no user exists for {email}".format(email=email))
            abort(400)
        return {"email": email}, 200

    def post(self, token):
        """
        Send the password reset email to the specified email address
        (recaptcha protected)
        Note that param "token" represents the raw email address
        of the recipient, and it is not expected to be encoded.

        :param token: email address of the recipient
        :type token: basestring
        """
        if token == current_app.config['BOOTSTRAP_USER_EMAIL']:
            abort(403)
        try:
            data = get_post_data(request)
            reset_url = data['reset_url']
        except (AttributeError, KeyError):
            return {'error': 'malformed request'}, 400
        if not verify_recaptcha(request):
            return {'error': 'captcha was not verified'}, 403

        u = user_manipulator.first(email=token)
        if u is None:
            return {'error': 'no such user exists'}, 404

        if not u.confirmed_at:
            return {'error': 'This email was never verified. It will be '
                             'deleted from out database within a day'}, 403
        send_email(
            email_addr=token,
            email_template=PasswordResetEmail,
            base_url=reset_url,
            payload=token
        )
        return {"message": "success"}, 200

    def put(self, token):
        """
        Check if the current user has the same email as the decoded token,
        and, if so, change that user's password to that specified in
        the PUT body

        :param token: HMAC encoded email string
        :type token: basestring
        """
        try:
            email = current_app.ts.loads(token,
                                         max_age=600,
                                         salt=PasswordResetEmail.salt)
        except:
            current_app.logger.critical(
                "PUT on reset-password with invalid token. "
                "This may indicate a brute-force attack!"
            )
            return {"error": "unknown verification token"}, 404

        try:
            data = get_post_data(request)
            new_password1 = data['password1']
            new_password2 = data['password2']
        except (AttributeError, KeyError):
            return {'error': 'malformed request'}, 400

        if new_password1 != new_password2:
            return {'error': 'passwords do not match'}, 400
        try:
            validate_password(new_password1)
        except ValidationError, e:
            return {'error': 'validation error'}, 400

        u = user_manipulator.first(email=email)
        if u is None:
            current_app.logger.error(
                "[PUT] Reset password validated link,"
                " but no user exists for {email}".format(email=email)
            )
            abort(500)
        user_manipulator.update(u, password=new_password1)
        logout_user()
        login_user(u)
        return {"message": "success"}, 200


class ChangePasswordView(Resource):
    """
    Implements change password functionality
    """
    decorators = [login_required]

    def post(self):
        """
        Verify that the current user's password is correct, that the desired
        new password is valid, and finally update the password in the User
        object
        """
        try:
            data = get_post_data(request)
            old_password = data['old_password']
            new_password1 = data['new_password1']
            new_password2 = data['new_password2']
        except (AttributeError, KeyError):
            return {'error': 'malformed request'}, 400

        if not current_user.validate_password(old_password):
            return {'error': 'please verify your current password'}, 401

        if new_password1 != new_password2:
            return {'error': 'passwords do not match'}, 400
        try:
            validate_password(new_password1)
        except ValidationError, e:
            return {'error': 'validation error'}, 400

        u = user_manipulator.first(email=current_user.email)
        user_manipulator.update(u, password=new_password1)
        return {'message': 'success'}, 200


class PersonalTokenView(Resource):
    """
    Implements getting/setting a personal API token
    """
    decorators = [
        ratelimit(500, 43200, scope_func=scope_func),
        login_required,
    ]

    def get(self):
        """
        This endpoint returns the ADS API client token, which
        is effectively a personal access token
        """
        client = OAuthClient.query.filter_by(
            user_id=current_user.get_id(),
            name=u'ADS API client',
        ).first()
        if not client:
            return {'message': 'no ADS API client found'}, 200

        token = OAuthToken.query.filter_by(
            client_id=client.client_id,
            user_id=current_user.get_id(),
        ).first()

        if not token:
            current_app.logger.error(
                'no ADS API client token '
                'found for {email}. This should not happen!'.format(
                    email=current_user.email
                )
            )
            return {'message': 'no ADS API token found'}, 500

        return print_token(token)

    def put(self):
        """
        Generates a new API key
        :return: dict containing the API key data structure
        """

        client = OAuthClient.query.filter_by(
            user_id=current_user.get_id(),
            name=u'ADS API client',
        ).first()

        if client is None:  # If no client exists, create a new one
            client = OAuthClient(
                user_id=current_user.get_id(),
                name=u'ADS API client',
                description=u'ADS API client',
                is_confidential=False,
                is_internal=True,
                _default_scopes=' '.join(
                    current_app.config['USER_API_DEFAULT_SCOPES']
                ),
            )
            client.gen_salt()

            token = OAuthToken(
                client_id=client.client_id,
                user_id=current_user.get_id(),
                access_token=gen_salt(40),
                refresh_token=gen_salt(40),
                expires=datetime.datetime(2500, 1, 1),
                _scopes=' '.join(
                    current_app.config['USER_API_DEFAULT_SCOPES']
                ),
                is_personal=False,
            )

            db.session.add(client)
            db.session.add(token)
            try:
                db.session.commit()
            except Exception, e:
                current_app.logger.error("Unknown DB error: {0}".format(e))
                abort(503)
            current_app.logger.info(
                "Created ADS API client+token for {0}".format(
                    current_user.email
                )
            )
        else:  # Client exists; find its token and change the access_key
            token = OAuthToken.query.filter_by(
                client_id=client.client_id,
                user_id=current_user.get_id(),
            ).first()
            token.access_token = gen_salt(40)

            db.session.add(token)
            try:
                db.session.commit()
            except Exception, e:
                db.session.rollback()
                current_app.logger.error("Unknown DB error: {0}".format(e))
                abort(503)
            current_app.logger.info(
                "Updated ADS API token for {0}".format(current_user.email)
            )
        return print_token(token)


class LogoutView(Resource):
    """
    View that calls flask.ext.login.logout_user()
    """
    def post(self):
        logout_user()
        return {"message": "success"}, 200


class ChangeEmailView(Resource):
    """
    Implements change email functionality
    """

    decorators = [
        ratelimit(5, 600, scope_func=scope_func),
        login_required,
    ]

    def post(self):
        """
        POST desired email and password to change the current user's email.
        Checks that the desired new email isn't already registerd

        This will create the new user. The encoded email payload will have
        a second argument `id` which is the id of the user making this
        request. We assume that the view responsible for verifying emails
        knows what to do with this extra argument. This should be deprecated
        by using signals in the future.
        """
        try:
            data = get_post_data(request)
            email = data['email']
            password = data['password']
            verify_url = data['verify_url']
        except (AttributeError, KeyError):
            return {'error': 'malformed request'}, 400

        u = user_manipulator.first(email=current_user.email)
        if not u.validate_password(password):
            abort(401)

        if user_manipulator.first(email=email) is not None:
            return {
                "error": "{0} has already been registered".format(email)
            }, 403
        send_email(
            email_addr=email,
            base_url=verify_url,
            email_template=VerificationEmail,
            payload=[email, u.id]
        )
        send_email(
            email_addr=current_user.email,
            email_template=EmailChangedNotification
        )
        user_manipulator.create(
            email=email,
            password=password,
            active=True,
            registered_at=datetime.datetime.now(),
            login_count=0,
        )
        return {"message": "success"}, 200


class UserAuthView(Resource):
    """
    Implements login and logout functionality
    """
    decorators = [ratelimit(30, 120, scope_func=scope_func)]

    def post(self):
        """
        Authenticate the user, logout the current user, login the new user
        :return: dict containing success message
        """
        try:
            data = get_post_data(request)
            email = data['username']
            password = data['password']
        except (AttributeError, KeyError):
            return {'error': 'malformed request'}, 400

        u = user_manipulator.first(email=email)
        if u is None or not u.validate_password(password):
            abort(401)
        if u.confirmed_at is None:
            return {"error": "account has not been verified"}, 403

        # Logout of previous user (may have been bumblebee)
        if current_user.is_authenticated():
            logout_user()
        login_user(u)  # Login to real user
        user_manipulator.update(
            u,
            last_login_at=datetime.datetime.now(),
            login_count=u.login_count+1 if u.login_count else 1,
        )
        return {"message": "success"}, 200


class VerifyEmailView(Resource):
    """
    Decode a TimerSerializer token into an email, returning an error message
    to the client if this task fails

    If the token is decoded, set User.confirm_at to datetime.now()
    """
    decorators = [ratelimit(20, 600, scope_func=scope_func)]

    def get(self, token):
        try:
            email = current_app.ts.loads(token,
                                         max_age=86400,
                                         salt=VerificationEmail.salt)
        except:
            current_app.logger.warning(
                "{0} verification token not validated".format(token)
            )
            return {"error": "unknown verification token"}, 404

        # This logic is necessary to de-activate accounts via the change-email
        # workflow. This strong coupling should be deprecated by using signals.
        previous_uid = None
        if " " in email:
            email, previous_uid = email.split()

        u = user_manipulator.first(email=email)
        if u is None:
            return {"error": "no user associated "
                             "with that verification token"}, 404
        if u.confirmed_at is not None:
            return {"error": "this user and email "
                             "has already been validated"}, 400
        if previous_uid:
            # De-activate previous accounts by deleting the account associated
            # with the new email address, then update the old account with the
            # new email address. Again, this should be deprecated with signals.
            user_manipulator.delete(u)
            u = user_manipulator.first(id=previous_uid)
            user_manipulator.update(
                u,
                email=email,
                confirmed_at=datetime.datetime.now()
            )
        else:
            user_manipulator.update(u, confirmed_at=datetime.datetime.now())
        login_user(u)
        return {"message": "success", "email": email}


class CSRFView(Resource):
    """
    Returns a csrf token
    """

    decorators = [ratelimit(50, 600, scope_func=scope_func)]

    def get(self):
        """
        Returns a csrf token
        """
        return {'csrf': generate_csrf()}


class UserRegistrationView(Resource):
    """
    Implements new user registration
    """

    decorators = [ratelimit(50, 600, scope_func=scope_func)]

    def post(self):
        """
        Standard user registration workflow;
        verifies that the email is available, creates a de-activated accounts,
        and sends verification email that serves to activate said account
        """
        try:
            data = get_post_data(request)
            email = data['email']
            password = data['password1']
            repeated = data['password2']
            verify_url = data['verify_url']
        except (AttributeError, KeyError):
            return {'error': 'malformed request'}, 400

        if not verify_recaptcha(request):
            return {'error': 'captcha was not verified'}, 403
        if password != repeated:
            return {'error': 'passwords do not match'}, 400
        try:
            validate_email(email)
            validate_password(password)
        except ValidationError, e:
            return {'error': 'validation error'}, 400

        if user_manipulator.first(email=email) is not None:
            return {'error': 'an account is already'
                             ' registered for {0}'.format(email)}, 409
        send_email(
            email_addr=email,
            base_url=verify_url,
            email_template=VerificationEmail,
            payload=email
        )
        u = user_manipulator.create(
            email=email,
            password=password,
            active=True,
            registered_at=datetime.datetime.now(),
            login_count=0,
        )
        return {"message": "success"}, 200


class Bootstrap(Resource):
    """
    Implements "bootstrap" functionality, which returns the data necessary
    for the bumblebee javascript client to authenticate and interact with
    other adsws-api resources.
    """

    def get(self):
        """
        If the current user is unauthenticated, or the current user
        is the "bootstrap" (anon) user, return/create a "BB Client" OAuthClient
        and token depending if "oauth_client" is encoded into their
        session cookie

        If the user is a authenticated as a real user, return/create
        a "BB Client" OAuthClient and token depending if that user already has
        one in the database
        """
        
        # rca: I'd like to register here my distaste for Flask-Restful and
        # how it divorces parameters; it was a big mistake to go with that framework
        # and the decision shouldn't have been left to inexperienced developers
        # this is not recommended solution, but even the recommended solution
        # is just awful: http://stackoverflow.com/questions/30779584/flask-restful-passing-parameters-to-get-request
        parser = reqparse.RequestParser()
        parser.add_argument('redirect_uri', type=str)
        parser.add_argument('scope', type=str)
        parser.add_argument('client_name', type=str)
        kwargs = parser.parse_args()
        
        scopes = kwargs.get('scope', None)
        client_name = kwargs.get('client_name', None)
        redirect_uri = kwargs.get('redirect_uri', None)
        
        # If we visit this endpoint and are unauthenticated, then login as
        # our anonymous user
        if not current_user.is_authenticated():
            login_user(user_manipulator.first(
                email=current_app.config['BOOTSTRAP_USER_EMAIL']
            ))
            
            if scopes or client_name:
                abort(401, "Sorry, you cant change scopes/name/redirect_uri of this user")

        if current_user.email == current_app.config['BOOTSTRAP_USER_EMAIL']:
            try:

                if 'oauth_client' in session:
                    client, token = Bootstrap.load_client(
                        session['oauth_client']
                    )
                else:
                    raise NoClientError('client/user mismatch')

                if client.user_id != int(current_user.get_id()):
                    raise NoClientError("client/user mistmatch")

            except (NoTokenError, NoClientError):
                client, token = Bootstrap.bootstrap_bumblebee()
                session['oauth_client'] = client.client_id
        else:
            client, token = Bootstrap.bootstrap_user()
            
            if scopes:
                client._default_scopes = scopes
            if redirect_uri:
                client._redirect_uris = redirect_uri
            if client_name:
                client.client_name = client_name

        client.last_activity = datetime.datetime.now()
        db.session.commit()
        output = print_token(token)
        
        output['client_id'] = client.client_id
        output['client_secret'] = client.client_secret
        
        return output

    @staticmethod
    def load_client(clientid):
        """
        Loads an Oauth2client from a client id string and returns that client
        and a valid oauth2token

        :param clientid: OAuthClient.client_id
        :type clientid: basestring
        :return: OAuthClient instance
        """
        client = OAuthClient.query.filter_by(
            client_id=clientid,
        ).first()

        if client is None:
            raise NoClientError("No client found")

        token = OAuthToken.query.filter_by(
            client_id=client.client_id,
            is_personal=False,
            is_internal=True,
        ).filter(OAuthToken.expires > datetime.datetime.now()).first()

        if token is None:
            raise NoTokenError("No valid token found")

        return client, token

    @staticmethod
    @ratelimit(400, 60*60*24, scope_func=scope_func)
    def bootstrap_bumblebee():
        """
        Return or create a OAuthClient owned by the "bumblebee" user.
        Re-uses an existing client if "oauth_client" is encoded into the
        session cookie, otherwise writes a new client to the database.

        Similar logic performed for the OAuthToken.

        :return: OAuthToken instance
        """
        assert current_user.email == current_app.config['BOOTSTRAP_USER_EMAIL']

        salt_length = current_app.config.get('OAUTH2_CLIENT_ID_SALT_LEN', 40)
        scopes = ' '.join(current_app.config.get('BOOTSTRAP_SCOPES', []))
        expires = current_app.config.get('BOOTSTRAP_TOKEN_EXPIRES', 3600*24)
        client_name = current_app.config.get('BOOTSTRAP_CLIENT_NAME', 'BB client')
        uid = current_user.get_id()

        client = OAuthClient(
            user_id=uid,
            name=client_name,
            description=client_name,
            is_confidential=False,
            is_internal=True,
            _default_scopes=scopes,
        )
        client.gen_salt()

        db.session.add(client)

        if isinstance(expires, int):
            expires = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=expires)

        token = OAuthToken(
            client_id=client.client_id,
            user_id=uid,
            expires=expires,
            _scopes=scopes,
            access_token=gen_salt(salt_length),
            refresh_token=gen_salt(salt_length),
            is_personal=False,
            is_internal=True,
        )

        db.session.add(token)
        db.session.commit()
        return client, token

    @staticmethod
    @ratelimit(100, 600, scope_func=scope_func)
    def bootstrap_user():
        """
        Return or create a OAuthClient owned by the authenticated real user.
        Re-uses an existing client if "oauth_client" is found in the database
        for this user, otherwise writes a new client to the database.

        Similar logic performed for the OAuthToken.

        :return: OAuthToken instance
        """
        assert current_user.email != current_app.config['BOOTSTRAP_USER_EMAIL']

        uid = current_user.get_id()
        client_name = current_app.config.get('BOOTSTRAP_CLIENT_NAME', 'BB client')

        client = OAuthClient.query.filter_by(
            user_id=uid,
            name=client_name,
        ).first()
        
        scopes = ' '.join(current_app.config['USER_DEFAULT_SCOPES'])
        salt_length = current_app.config.get('OAUTH2_CLIENT_ID_SALT_LEN', 40)

        if client is None:
            client = OAuthClient(
                user_id=current_user.get_id(),
                name=client_name,
                description=client_name,
                is_confidential=True,
                is_internal=True,
                _default_scopes=scopes,
            )
            client.gen_salt()
            db.session.add(client)

            token = OAuthToken(
                client_id=client.client_id,
                user_id=uid,
                access_token=gen_salt(salt_length),
                refresh_token=gen_salt(salt_length),
                expires=datetime.datetime(2500, 1, 1),
                _scopes=scopes,
                is_personal=False,
                is_internal=True,
            )
            db.session.add(token)
            current_app.logger.info(
                "Created BB client for {email}".format(email=current_user.email)
            )
        else:
            token = OAuthToken.query.filter_by(
                client_id=client.client_id,
                user_id=current_user.get_id(),
            ).first()

            if token is None:
                # the token was not created yet
                token = OAuthToken(
                    client_id=client.client_id,
                    user_id=uid,
                    access_token=gen_salt(salt_length),
                    refresh_token=gen_salt(salt_length),
                    expires=datetime.datetime(2500, 1, 1),
                    _scopes=scopes,
                    is_personal=False,
                    is_internal=True,
                )
                db.session.add(token)
                current_app.logger.info(
                    "Created BB client for {email}".format(email=current_user.email)
                )   
        
        db.session.commit()
        return client, token

