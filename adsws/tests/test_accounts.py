from flask.ext.testing import TestCase
from flask.ext.login import current_user
from flask.sessions import SecureCookieSessionInterface
from flask import current_app, url_for, session

from adsws.core import db, user_manipulator
from adsws.testsuite import make_test_suite, run_test_suite
from adsws import accounts
from adsws.accounts import utils
from adsws.accounts.emails import PasswordResetEmail, VerificationEmail
from adsws.modules.oauth2server.models import OAuthClient, OAuthToken
from sqlalchemy import func

from unittest import TestCase as UnitTestCase

import mock
import json
import requests
import datetime
import httpretty
import random
import hashlib, binascii

RATELIMIT_KEY_PREFIX = 'unittest.{0}'.format(datetime.datetime.now())



class TestUtils(UnitTestCase):
    """Test account validation utilities"""

    def test_get_post_data(self):
        class FakeRequest:
            """Serves as a mock flask.request object"""
            pass

        request = FakeRequest()
        request.values = "format=form"
        request.get_json = lambda **x: {'format': 'json'}

        # empty content-type -> default to json
        data = utils.get_post_data(request)
        self.assertEqual(data, request.get_json())

        # raise some exception when it tries to run get_json(force=true)
        request.get_json = lambda **x: {}.not_a_method()
        data = utils.get_post_data(request)
        self.assertEqual(data, request.values)

    def test_validate_email(self):
        err, func = utils.ValidationError, utils.validate_email  # shorthand
        self.assertRaises(err, func, "invalidemail")  # No "@" symbol
        self.assertRaises(err, func, "invalid@ email")  # whitespace is invalid
        self.assertTrue(func('@'))

    def test_validate_password(self):
        err, func = utils.ValidationError, utils.validate_password  # shorthand
        self.assertRaises(err, func, "n0")
        self.assertTrue(func("123Aabc"))


class AccountsSetup(TestCase):
    def tearDown(self):
        # [hack]
        # When testing, an app is created for every single test but the limiter is
        # always the same. We make sure that the new app forgets about routes and
        # limits set with the previous app instance (or limit registration will be
        # triggered more than once)
        self.app.extensions['limiter'].forget()
        # [/hack]
        httpretty.disable()
        httpretty.reset()
        self.bootstrap_user = None
        self.real_user = None
        db.drop_all(app=self.app)

    def setUp(self):
        db.create_all(app=self.app)
        self.bootstrap_user = user_manipulator.create(
            email=self.app.config['BOOTSTRAP_USER_EMAIL'],
            password='bootstrap',
            active=True
        )
        self.real_user = user_manipulator.create(
            email='real_user@unittests',
            password='user',
            active=True,
        )
        self.passwords = {
            self.bootstrap_user:'bootstrap',
            self.real_user: 'user',
        }

    def create_app(self):
        app = accounts.create_app(
            SQLALCHEMY_BINDS=None,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            TESTING=False,
            DEBUG=False,
            SITE_SECURE_URL='http://localhost',
            GOOGLE_RECAPTCHA_ENDPOINT='http://google.com/verify_recaptcha',
            GOOGLE_RECAPTCHA_PRIVATE_KEY='fake_recaptcha_key',
            SECURITY_REGISTER_BLUEPRINT=False,
            BOOTSTRAP_USER_EMAIL='bootstrap_user@unittests',
            MAIL_SUPPRESS_SEND=True,
            RATELIMIT_KEY_PREFIX=RATELIMIT_KEY_PREFIX,
            SECRET_KEY="unittests-secret-key",
            SQLALCHEMY_ECHO=False
        )
        return app


class TestAccounts(AccountsSetup):
    """
    Tests for accounts endpoints and workflows
    """

    def _create_client(self, client_id='test', user_id=0, scopes='adsws:internal'):
        # create a client in the database
        c1 = OAuthClient(
            client_id=client_id,
            client_secret='client secret %s' % random.random(),
            name='bumblebee',
            description='',
            is_confidential=False,
            user_id=user_id,
            _redirect_uris='%s/client/authorized' % self.app.config.get('SITE_SECURE_URL'),
            _default_scopes=scopes
        )
        db.session.add(c1)
        db.session.commit()
        return OAuthClient.query.filter_by(client_secret=c1.client_secret).one()

    def _create_token(self, client_id='test', user_id=0, scopes='adsws:internal'):
        token = OAuthToken(
                client_id=client_id,
                user_id=user_id,
                access_token='access token %s' % random.random(),
                refresh_token='refresh token %s' % random.random(),
                expires=datetime.datetime(2500, 1, 1),
                _scopes=scopes,
                is_personal=False,
                is_internal=True,
            )
        db.session.add(token)
        db.session.commit()
        return OAuthToken.query.filter_by(id=token.id).one()

    def test_user_info(self):
        with self.client as c:
            account_data = self.real_user.id
            url = url_for('userinfoview', account_data=account_data)
            # Unauthenticated should return 401
            r = c.get(url)
            self.assertStatus(r, 401)

            client = self._create_client('priviledged_client_id', self.real_user.id, scopes='adsws:internal')
            token = self._create_token('priviledged_client_id', self.real_user.id, scopes='adsws:internal')

            user_id = self.real_user.id
            client_id = client.client_id
            expected_hashed_user_id = binascii.hexlify(hashlib.pbkdf2_hmac('sha256', str(user_id), current_app.secret_key, 10, dklen=32)) if user_id else None
            expected_hashed_client_id = binascii.hexlify(hashlib.pbkdf2_hmac('sha256', str(client_id), current_app.secret_key, 10, dklen=32)) if client_id else None

            # Authenticated requests (using a client that has the required scope)
            # and using an 1) user id
            headers={'Authorization': 'Bearer:{}'.format(token.access_token)}
            r = c.get(url, headers=headers)
            self.assertStatus(r, 200)
            self.assertEqual(r.json['hashed_user_id'], expected_hashed_user_id)
            self.assertEqual(r.json['hashed_client_id'], expected_hashed_client_id)
            self.assertFalse(r.json['anonymous'])
            self.assertEqual(r.json['source'], 'user_id')
            expected_json = r.json

            # 2) access token
            account_data = token.access_token
            url = url_for('userinfoview', account_data=account_data)
            r = c.get(url, headers=headers)
            self.assertStatus(r, 200)
            expected_json['source'] = u'access_token'
            self.assertEqual(r.json, expected_json)

            # 3) client id
            account_data = client.client_id
            url = url_for('userinfoview', account_data=account_data)
            r = c.get(url, headers=headers)
            self.assertStatus(r, 200)
            expected_json['source'] = u'client_id'
            self.assertEqual(r.json, expected_json)

            # 4) session
            #
            # Encode first a session cookie using the current app secret:
            sscsi = SecureCookieSessionInterface()
            signingSerializer = sscsi.get_signing_serializer(current_app)
            session = signingSerializer.dumps({'_id': 'session_id', 'oauth_client': client.client_id})

            account_data = session
            url = url_for('userinfoview', account_data=account_data)
            r = c.get(url, headers=headers)
            self.assertStatus(r, 200)
            expected_json['source'] = u'session:client_id'
            self.assertEqual(r.json, expected_json)


    def setup_google_recaptcha_response(self):
        """Set up a mock google recaptcha api"""

        #  httpretty socket blocks if enabled before calling self.get_csrf() !
        httpretty.enable()
        url = current_app.config['GOOGLE_RECAPTCHA_ENDPOINT']

        def callback(request, uri, headers):
            data = request.parsed_body
            if data['response'][0] == 'correct_response':
                res = {'success': True}
            elif data['response'][0] == 'incorrect_response':
                res = {'success': False}
            elif data['response'][0] == 'dont_return_200':
                return 503, headers, "Service Unavailable"
            else:
                raise Exception(
                    "This case is not expected by the tests: {0}".format(data)
                )
            return 200, headers, json.dumps(res)
        httpretty.register_uri(httpretty.POST, url, body=callback, content_type='application/json')

    def test_401_no_challenge(self):
        """
        Test that a 401 response does not include a WWW-Authenticate header, which the browser
        will respond to by opening a login prompt
        """
        urls = [url_for(i) for i in ['oauthprotectedview', 'personaltokenview']]
        for url in urls:
            r = self.client.get(url)
            self.assertNotIn(
                'WWW-Authenticate', r.headers,
                msg='challenge issued on {0}'.format(url)
            )

    def get_csrf(self):
        """
        Returns a csrf token by visiting /bootstrap
        :return: string containing the csrf token bound to the current session
        """

        #  httpretty socket blocks if enabled before calling self.get_csrf() !
        r = self.client.get(url_for('csrfview'))
        return r.json['csrf']

    def login(self, user, client, csrf):
        """
        Perform the necessary steps required to sucessfully login

        Assumes that the resuling cookie will be saved, i.e. we are in a
        flask.client session context.

        :param user: User object whose confirmed_at attribute to set, and then
        logged in
        :param client: flask.client instance
        :param csrf: csrf token
        """
        user_manipulator.update(
            user,
            confirmed_at=datetime.datetime.now()
        )
        passwd = self.passwords[user]
        payload = {'username': user.email,'password': passwd}
        r = client.post(
            url_for('userauthview'),
            data=json.dumps(payload),
            headers={'content-type': 'application/json', 'X-CSRFToken': csrf},
        )
        self.assertStatus(r, 200)

    def test_delete_account(self):
        """
        Test the delete account workflow
        """
        url = url_for('deleteaccountview')
        with self.client as c:
            csrf = self.get_csrf()

            # CSRF not passed; should return 400
            r = c.post(url)
            self.assertStatus(r, 400)

            # Not authenticated; should 401
            r = c.post(url,headers={'X-CSRFToken':csrf})
            self.assertStatus(r,401)

            # Login and passing the correct csrf should delete the acct
            self.login(self.real_user, c, csrf)
            r = c.post(url,headers={'X-CSRFToken':csrf})
            self.assertStatus(r, 200)
            u = user_manipulator.first(email=self.real_user.email)
            self.assertIsNone(u)

    def test_adsapi_token_workflow(self):
        """
        test getting and resetting the personal access token (ADS-API client)
        """
        url = url_for('personaltokenview')
        with self.client as c:
            csrf = self.get_csrf()

            # Unauthenticated should return 401
            r = c.get(url)
            self.assertStatus(r, 401)

            self.login(self.real_user, c, csrf)

            # no api client has yet been registered. We explicitly choose
            # not to automatically create this client as part of the user
            # registration workflow
            r = c.get(url)
            self.assertEqual(r.json['message'], 'no ADS API client found')

            # No CSRF token passed should return 400
            r = c.put(url)
            self.assertStatus(r, 400)

            # PUT to make the API client and access token
            r = c.put(
                url,
                headers={'content-type': 'application/json', 'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 200)
            self.assertIn('access_token', r.json)
            tok = r.json['access_token']

            # GET should return the same access token
            r = c.get(url)
            self.assertEqual(tok,r.json['access_token'])

            # PUT should generate a new access_token
            r = c.put(
                url,
                headers={'content-type': 'application/json', 'X-CSRFToken': csrf}
            )
            self.assertNotEqual(tok, r.json['access_token'])
            tok2 = r.json['access_token']
            self.assertNotEqual(tok, tok2)

            # GET should return the updated token (tok2) and not the old one
            # (tok)
            r = c.get(url)
            self.assertEqual(tok2, r.json['access_token'])

    def test_change_email(self):
        """
        Test the change email workflow.

        The workflow is tightly coupled with the verify-email workflow, which
        should be de-coupled by using signals in the future
        """
        url = url_for('changeemailview')
        with self.client as c:
            csrf = self.get_csrf()
            self.setup_google_recaptcha_response()

            # Unauthenticated should return 401
            r = c.post(url, headers={'X-CSRFToken': csrf})
            self.assertStatus(r, 401)

            self.login(self.real_user, c, csrf)

            # incorrect password, even though we're logged in should return 401
            payload = {
                'email': self.real_user.email,
                'password': 'not_correct',
                'verify_url': 'http://not_relevant.com'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf},
            )
            self.assertStatus(r, 401)

            # correct password, but that email is already registered
            payload = {
                'email': self.bootstrap_user.email,
                'password': self.passwords[self.real_user],
                'verify_url': 'http://not_relevant.com'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf},
            )
            self.assertStatus(r, 403)

            # valid end-to-end workflow
            previous_email = self.real_user.email
            payload = {
                'email': 'changed@email',
                'password': self.passwords[self.real_user],
                'verify_url': 'http://not_relevant.com'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 200)

            u = user_manipulator.first(email='changed@email')
            self.assertIsNotNone(u)
            self.assertIsNone(u.confirmed_at)
            self.assertIsNotNone(
                user_manipulator.first(email=previous_email)
            )
            self.assertIsNotNone(
                user_manipulator.first(email=previous_email).confirmed_at
            )
            self.assertNotEqual(self.real_user.email, "changed@email")

            # Get the token that this view will send, send it to the
            # verfication email endpoint, and check that the user's email
            # was correctly updated
            msg, token = utils.send_email(
                email_addr="changed@email",
                email_template=VerificationEmail,
                payload = ["changed@email", self.real_user.id],
            )

            url = url_for('verifyemailview', token=token)
            r = self.client.get(url)
            self.assertStatus(r, 200)
            self.assertIsNone(
                user_manipulator.first(email=previous_email)
            )
            self.assertEqual(self.real_user.email, "changed@email")

    def test_reset_password(self):
        """
        test the reset password workflow
        """
        with self.client as c:
            csrf = self.get_csrf()
            self.setup_google_recaptcha_response()
            user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())

            url = url_for(
                'forgotpasswordview',
                token="this_email_wasnt@registered"
            )
            payload = {
                'g-recaptcha-response': 'correct_response',
                'reset_url':'http://not_relevant.com',
            }

            # Attempt to reset the password for an unregistered email address
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken':csrf}
            )
            self.assertStatus(r, 404)
            self.assertEqual(r.json['error'], 'no such user exists')

            # Resetting password for the default user should not be permitted
            url = url_for(
                'forgotpasswordview',
                token=self.bootstrap_user.email
            )
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 403)

            # Test a proper change-email request
            url = url_for('forgotpasswordview', token=self.real_user.email)
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 200)

            # Now let's test GET and PUT requests with the encoded token
            msg, token = utils.send_email(
                email_addr=self.real_user.email,
                email_template=PasswordResetEmail,
                payload=self.real_user.email
            )
            url = url_for('forgotpasswordview', token=token)

            # Test de-coding and verifying of the token
            r = c.get(url)
            self.assertStatus(r, 200)
            self.assertEqual(r.json['email'], self.real_user.email)

            # Change the password, then attempt to log-in with the new password
            payload = {'password1': '123Abc', 'password2': '123Abc'}
            r = c.put(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken':csrf}
            )
            self.assertStatus(r, 200)

            url = url_for('userauthview')
            payload = {'username': self.real_user.email,'password':'123Abc'}
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 200)
            self.assertEqual(current_user.email, self.real_user.email)

    def test_email_verification(self):
        """
        Test encoding an email, and see if it
        can be resolved with the verify endpoint
        """

        # Even though we have a a valid token, no user was registered with this
        # email address. This should never happen in normal use.
        msg, token = utils.send_email(
            email_addr="this_email_wasnt@registered",
            base_url='localhost',
            email_template=VerificationEmail,
            payload="this_email_wasnt@registered"
        )
        self.assertIn("localhost", msg.html)

        url = url_for('verifyemailview', token=token)
        r = self.client.get(url)
        self.assertStatus(r, 404)
        self.assertEqual(r.json['error'],"no user associated with that "
                                         "verification token")

        # Test for an inproperly encoded email, expect 404
        r = self.client.get(url+"incorrect")
        self.assertStatus(r, 404)
        self.assertEqual(r.json['error'], 'unknown verification token')


        # Test a valid token with a registered user
        msg, token = utils.send_email(
            email_addr=self.real_user.email,
            email_template=VerificationEmail,
            payload=self.real_user.email
        )
        url = url_for('verifyemailview', token=token)
        r = self.client.get(url)
        self.assertStatus(r, 200)
        self.assertEqual(r.json["email"], self.real_user.email)
        self.assertIsInstance(self.real_user.confirmed_at, datetime.date)
        self.assertAlmostEqual(
            self.real_user.confirmed_at,
            datetime.datetime.now(),
            delta=datetime.timedelta(seconds=1),
        )


        # Test for an already confirmed email
        r = self.client.get(url)
        self.assertStatus(r, 400)
        self.assertEqual(r.json["error"], "this user and email has already "
                                          "been validated")

    def test_verify_google_recaptcha(self):
        """
        Test the function responsible for contacting the google recaptcha API
        and verifying the captcha response, using a mocked API
        """
        self.setup_google_recaptcha_response()

        # Set up a fake request object that will be passed directly to
        # the function being tested
        class FakeRequest:  pass
        fakerequest = FakeRequest()
        fakerequest.remote_addr = 'placeholder'

        # Test a "success" response
        fakerequest.get_json = lambda **x: \
            {'g-recaptcha-response': 'correct_response'}
        res = utils.verify_recaptcha(fakerequest)
        self.assertTrue(res)

        # Test a "fail" response
        fakerequest.get_json = lambda **x: \
            {'g-recaptcha-response': 'incorrect_response'}
        res = utils.verify_recaptcha(fakerequest)
        self.assertFalse(res)

        # Test a 503 response
        fakerequest.get_json = lambda **x: \
            {'g-recaptcha-response': 'dont_return_200'}
        self.assertRaises(
            requests.HTTPError,
            utils.verify_recaptcha,
            fakerequest
        )

        # Test a malformed request
        fakerequest = FakeRequest()
        self.assertRaises(
            (KeyError, AttributeError),
            utils.verify_recaptcha,
            fakerequest
        )

    def test_login_and_logout(self):
        """
        tests a login and logout pattern, including incorrect login
        """
        url = url_for('userauthview')

        payload = {'username': 'foo', 'password': 'bar'}
        r = self.client.post(
            url,
            data=json.dumps(payload),
            headers={'content-type': 'application/json'}
        )
        self.assertStatus(r, 400)  # No csrf token = 400

        with self.client as c:
            csrf = self.get_csrf()

            # Incorrect login should return 401
            payload = {'username': 'foo', 'password': 'bar'}
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 401)

            # A correct login, but unverified account should return an error
            payload = {
                'username': self.real_user.email,
                'password': self.passwords[self.real_user]}
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 403)
            self.assertEqual(r.json['error'], 'account has not been verified')

            # Correct login on a verified account
            user_manipulator.update(
                self.real_user,
                confirmed_at=datetime.datetime.now()
            )
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf},
            )
            self.assertStatus(r, 200)
            self.assertEqual(current_user.email, self.real_user.email)
            self.assertEqual(current_user.login_count, 1)
            self.assertIsInstance(current_user.last_login_at, datetime.date)
            self.assertAlmostEqual(
               current_user.last_login_at,
               datetime.datetime.now(),
               delta=datetime.timedelta(seconds=1),
            )

            # Test logout
            r = c.post(url_for('logoutview'),headers={'X-CSRFToken': csrf})
            self.assertRaises(AttributeError, lambda: current_user.email)

    def test_bootstrap_bumblebee(self):
        """
        test the bootstrap bumblebee functionality, namely that
        a. logins an anon user as the bumblebee user,
        b. returns the correct bootstrap data structure, and
        c. does not return an expired OAuth token
        """

        url = url_for('bootstrap')
        with self.client as c:

            # Assert that we get the token, and that we are logged in as the
            # bumblebee user
            r = c.get(url)
            self.assertEqual(r.json['username'], self.bootstrap_user.email)
            self.assertEqual(current_user.email, self.bootstrap_user.email)
            self.assertTrue(r.json['anonymous'])
            for k in ['access_token', 'expire_in', 'scopes', 'token_type',
                      'username', 'refresh_token', 'ratelimit']:
                self.assertIn(
                    k, r.json,
                    msg="{k} not in {data}".format(k=k, data=r.json)
                )
                self.assertIsNotNone(
                    r.json[k],
                    msg="data[\"{k}\"] is None".format(k=k)
                )
            first_tok = r.json['access_token']

            # Visiting the OAuthProtectedView with this bearer token should
            # return 200
            r = c.get(
                url_for('oauthprotectedview'),
                headers={
                    "Authorization": "Bearer {0}".format(first_tok)
                }
            )
            self.assertStatus(r, 200)

            # Now manually expire the token, and make sure that re-visting
            # /bootstrap does not give back the expired token
            from adsws.modules.oauth2server.models import OAuthToken
            tok = db.session.query(OAuthToken).filter_by(
                access_token=first_tok).one()
            tok.expires = datetime.datetime.now()
            db.session.commit()

            # Test that the client has an updated last_activity attribute
            from adsws.modules.oauth2server.models import OAuthClient
            client = db.session.query(OAuthClient).filter_by(
                client_id=tok.client_id
            ).one()
            self.assertIsInstance(client.last_activity, datetime.date)
            self.assertAlmostEqual(
                client.last_activity,
                datetime.datetime.now(),
                delta=datetime.timedelta(seconds=1),
            )

            # re-visit the bootstrap URL, test to see if we get a fresh token
            r = c.get(url)
            self.assertNotEqual(r.json['access_token'], tok.access_token)
            self.assertTrue(r.json['anonymous'])

    def test_bootstrap_user(self):
        """
        test the bootstrap workflow for an authenticated real user.
        """
        url = url_for('bootstrap')
        with self.client as c:
            csrf = self.get_csrf()
            self.login(self.real_user, c, csrf)

            # Visiting bootstrap should return the data structure necessary
            # for the bumblebee javascript client, and specifically contain
            # that authenticated user's data
            r = c.get(url)
            for k in ['access_token', 'expire_in', 'scopes', 'token_type',
                      'username', 'refresh_token', 'ratelimit']:
                self.assertIn(
                    k, r.json,
                    msg="{k} not in {data}".format(k=k, data=r.json)
                )
                self.assertIsNotNone(
                    r.json[k],
                    msg="data[\"{k}\"] is None".format(k=k)
                )
            self.assertEqual(r.json['username'], self.real_user.email)
            self.assertEqual(current_user.email, self.real_user.email)
            self.assertEqual(
                r.json['scopes'], current_app.config['USER_DEFAULT_SCOPES']
            )
            self.assertFalse(r.json['anonymous'])

            # Visiting the OAuthProtectedView with this bearer token should
            # return 200
            r = c.get(
                url_for('oauthprotectedview'),
                headers={
                    "Authorization": "Bearer {0}".format(r.json['access_token'])
                }
            )
            self.assertStatus(r, 200)

    def test_bootstrap_api(self):
        """
        test the bootstrap workflow with api key
        """
        
        #
        url = url_for('bootstrap')
        client = self._create_client('priviledged_client_id', self.real_user.id, scopes='adsws:internal')
        token = self._create_token('priviledged_client_id', self.real_user.id, scopes='adsws:internal')
        headers = {'Authorization': 'Bearer %s' % token.access_token}

        # create a new oauth application
        with self.client as c:
            r = c.get(url, query_string={'ratelimit': 0.5, 'create_new': True}, headers=headers)
            j = r.json
            assert j['username'] == 'real_user@unittests'
            assert j['ratelimit'] == 0.5
            assert j['client_id'] != client.client_id
            assert j['scopes'] == ['user']
            x = db.session.query(OAuthClient).filter_by(client_id=j['client_id']).one()
            assert x.user_id == self.real_user.id
            assert x.ratelimit == 0.5
            assert x._default_scopes == 'user'
            used = db.session.query(func.sum(OAuthClient.ratelimit).label('sum')).filter(OAuthClient.user_id==current_user.get_id()).first()[0] or 0.0
            assert used == 0.5
        
        # create a bigger application
        with self.client as c:
            r = c.get(url, query_string={'ratelimit': 1.4, 'create_new': True}, headers=headers)
            j = r.json
            assert j['username'] == 'real_user@unittests'
            assert j['ratelimit'] == 1.4
            assert j['client_id'] != client.client_id
            assert j['scopes'] == ['user']
            x = db.session.query(OAuthClient).filter_by(client_id=j['client_id']).one()
            assert x.user_id == self.real_user.id
            assert x.ratelimit == 1.4
            assert x._default_scopes == 'user'
            used = db.session.query(func.sum(OAuthClient.ratelimit).label('sum')).filter(OAuthClient.user_id==current_user.get_id()).first()[0] or 0.0
            assert used == 1.9
        
        # try to go over the limit
        with self.client as c:
            r = c.get(url, query_string={'ratelimit': 0.2, 'create_new': True}, headers=headers)
            j = r.json
            assert j == {'error': 'The current user account does not have enough capacity to create a new client. Requested: 0.2, Available: 0.1'}
    
        with self.client as c:
            r = c.get(url, query_string={'ratelimit': 0.01, 'create_new': True}, headers=headers)
            used = db.session.query(func.sum(OAuthClient.ratelimit).label('sum')).filter(OAuthClient.user_id==current_user.get_id()).first()[0] or 0.0
            assert used == 1.91
            
        # instead of creating a new client, update an existing; this should automatically
        # grab the latest client (or use client_name to find the right one)
        with self.client as c:
            r = c.get(url, query_string={'ratelimit': 0.0, 'create_new': False}, headers=headers)
            used = db.session.query(func.sum(OAuthClient.ratelimit).label('sum')).filter(OAuthClient.user_id==current_user.get_id()).first()[0] or 0.0
            assert used == 1.90
            
            # now lets use this new client to access api
            headers['Authorization'] = 'Bearer %s' % r.json['access_token']
        
        # TODO: this should not work but it seems something is off with the ratelimiter
        # itself for adsws.accounts (it doesn't work there); to be revisited - I have 
        # another test inside test_accounts to check this functionality
        with self.client as c:
            r = c.get(url_for('personaltokenview'), headers=headers)
            
        # this should result in error
        with self.client as c:
            r = c.get(url, query_string={'ratelimit': 0.01, 'create_new': True, 'scope': 'ads:internal'}, headers=headers)
            assert r.json == {u'error': u'You have requested a scope not available to the current user'}
            assert r.status_code == 400
        
        
        # and a client without any session and without any api key
        atoken = ''        
        with self.client as c:
            c.cookie_jar.clear()
            r = c.get(url, query_string={'create_new': True}, headers={})
            j = r.json
            assert r.status_code == 200
            assert j['username'] == 'bootstrap_user@unittests'
            assert j['ratelimit'] == 1.0
            assert j['scopes'] == []
            token = j['access_token']
            
            # tryin again, should give us the same token
            r = c.get(url, headers={})
            assert r.json['access_token'] == token
            
            c.cookie_jar.clear()
            r = c.get(url, headers={'Authorization': 'Bearer %s' % token})
            assert r.json['access_token'] == token

        
    def test_change_password(self):
        """
        test change password workflow
        """
        url = url_for('changepasswordview')
        with self.client as c:
            csrf = self.get_csrf()

            # no csrf token should return a 400
            r = c.post(url, headers={'content-type': 'application/json'})
            self.assertStatus(r, 400)

            # test an unauthenticated request
            r = c.post(url, headers={'X-CSRFToken': csrf})
            self.assertStatus(r, 401)

            self.login(self.real_user, c, csrf)

            # authenticated request, but incorrect old_passwords should return
            # 401
            payload = {
                'old_password': 'wrong_password!',
                'new_password2': 'foo',
                'new_password1': 'foo'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 401)
            self.assertEqual(r.json['error'], 'please verify your current '
                                              'password')

            # a proper request should cause the user's password to be updated
            payload = {
                'old_password': self.passwords[self.real_user],
                'new_password2': '123Abc',
                'new_password1': '123Abc'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf})
            self.assertStatus(r, 200)
            self.assertEqual(r.json['message'], 'success')
            self.assertTrue(self.real_user.validate_password('123Abc'))

    def test_register_user(self):
        """
        test user registration
        """
        url = url_for('userregistrationview')
        with self.client as c:
            csrf = self.get_csrf()
            self.setup_google_recaptcha_response()

            # posting without a csrf token should return 400
            r = c.post(url)
            self.assertStatus(r, 400)

            # Giving incorrect input should return 400
            payload = {'email': 'me@email'}
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 400)

            # Test that registering an already registered email returns 409
            payload = {
                'email': self.real_user.email,
                'password1': 'Password1',
                'password2': 'Password1',
                'g-recaptcha-response': 'correct_response',
                'verify_url': 'http://not_relevant.com'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 409)

            # Test a valid new user registration
            payload = {
                'email': 'me@email',
                'password1': 'Password1',
                'password2': 'Password1',
                'g-recaptcha-response': 'correct_response',
                'verify_url': 'http://not_relevant.com'
            }
            r = c.post(
                url,
                data=json.dumps(payload),
                headers={'X-CSRFToken': csrf}
            )
            self.assertStatus(r, 200)
            u = user_manipulator.first(email="me@email")
            self.assertIsNotNone(u)
            self.assertIsNone(u.confirmed_at)

    def test_repeated_bootstrap(self):
        """
        This should ensure that if bootstrap is repeated it works as expected
        """
        with self.client as c:
            url = url_for('bootstrap')
            r1 = c.get(url)

            r2 = c.get(url)

            self.assertEqual(r1.json, r2.json)

    def test_utils_logout(self):
        """
        Tests that certain values are cleaned up when someone logs out
        """
        with self.client as c:

            url = url_for('bootstrap')
            c.get(url)

            csrf = self.get_csrf()
            self.login(self.real_user, c, csrf)

            utils.logout_user()

            self.assertNotIn('oauth_client', session)

    @mock.patch('adsws.accounts.views.Bootstrap.load_client')
    def test_when_no_session(self, mocked):
        """
        When there is no OAuth client within the session cookie, we do not need to access the database.

        Fresh session should have no OAuth client, and so should not call load_client
        Second bootstrap should have a BB client token, and so should call load_client
        """
        with self.client as c:

            url = url_for('bootstrap')
            c.get(url)
            self.assertFalse(mocked.called)

        with self.client as c:
            url = url_for('bootstrap')
            c.get(url)
            self.assertTrue(mocked.called)


TESTSUITE = make_test_suite(TestAccounts, TestUtils)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
