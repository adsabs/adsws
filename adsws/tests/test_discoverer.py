from flask import current_app, g
from adsws.core import user_manipulator
from api_base import ApiTestCase
from adsws import api
import subprocess
import os
import time
from sample_microservice import Stubdata
import mock

LIVESERVER_WAIT_SECONDS = 2.5


class DiscovererTestCase:
    """
    Base class for LocalModuleTestCase and RemoteModuleTestCase
    Responsible for testing the bootstrapped sample application's behavior
    """

    @classmethod
    def setupRemoteServer(cls):
        """
        Sets up a remote server using subprocess.Popen. The port is hardcoded
        as 5005
        """
        path = os.path.join(
            os.path.dirname(__file__),
            'sample_microservice',
            'app.py'
        )
        cls.liveserver = subprocess.Popen(['python', path])
        time.sleep(LIVESERVER_WAIT_SECONDS)

    @classmethod
    def tearDownRemoteServer(cls):
        """
        Kills the subprocess running the liveserver
        """
        cls.liveserver.kill()
        time.sleep(LIVESERVER_WAIT_SECONDS)

    def open(self, method, url, **kwargs):
        """
        Wrapper around client.open responsible for adding in the correct
        Authorization: Bearer token. Takes same parameters are client.open
        """
        return self.client.open(
            url,
            method=method,
            headers={"Authorization": "Bearer {0}".format(self.token)},
            **kwargs
        )

    def test_status_route(self):
        """
        the status route on the parent api should be accessible
        """
        r = self.open('GET', '/status')
        self.assertStatus(r, 200)

    def test_protected_route(self):
        """
        the protected route on the parent api should be accessible
        """
        r = self.open('GET', '/protected')
        self.assertStatus(r, 200)

    def test_resources_route(self):
        """
        Resources on the bootstrapped app should be accessible
        """
        r = self.open('GET', '/test_webservice/resources')
        self.assertStatus(r, 200)

    def test_410_resc(self):
        """
        Test that the response code is properly forwarded through adsws
        """
        r = self.open('GET', '/test_webservice/410')
        self.assertStatus(r, 410)

    def test_GET_resc(self):
        """
        test sample application GET resource
        """
        r = self.open('GET', '/test_webservice/GET')
        self.assertEqual(r.json, Stubdata.GET)

        r = self.open('POST', '/test_webservice/GET')
        self.assertStatus(r, 405)

    def test_POST_resc(self):
        """
        test sample application POST resource
        """
        r = self.open('POST', '/test_webservice/POST')
        self.assertEqual(r.json, Stubdata.POST)

        r = self.open('GET', '/test_webservice/POST')
        self.assertStatus(r, 405)

    def test_PUT_resc(self):
        """
        test sample application POST resource
        """
        r = self.open('PUT', '/test_webservice/PUT')
        self.assertEqual(r.json, Stubdata.PUT)

        r = self.open('GET', '/test_webservice/POST')
        self.assertStatus(r, 405)

    def test_DELETE_resc(self):
        """
        test sample application DELETE resource
        """
        r = self.open('DELETE', '/test_webservice/DELETE')
        self.assertEqual(r.json, Stubdata.DELETE)

        r = self.open('GET', '/test_webservice/DELETE')
        self.assertStatus(r, 405)

    def test_GETPOST_resc(self):
        """
        test sample application GETPOST resource
        """
        r = self.open('POST', '/test_webservice/GETPOST')
        self.assertEqual(r.json, Stubdata.GETPOST['POST'])

        r = self.open('GET', '/test_webservice/GETPOST')
        self.assertEqual(r.json, Stubdata.GETPOST['GET'])

    def test_SCOPED(self):
        """
        test sample application SCOPED resource, which should return 401
        """
        r = self.open('GET', '/test_webservice/SCOPED')
        self.assertStatus(r, 401)

    def test_headers(self):
        """
        test that a Cache-Control header is returned
        """
        r = self.open('GET','/test_webservice/GET')
        self.assertIn('Cache-Control', r.headers)

    def test_LOW_RATE_LIMIT(self):
        """
        test sample application ratelimited resource, including hitting the
        the limit and waiting until the limit is expired
        """
        go = lambda: self.open('GET', '/test_webservice/LOW_RATE_LIMIT')
        r = go()
        self.assertStatus(r, 200)
        self.assertEqual(g._rate_limit_info.remaining, 2)
        r = go()
        self.assertStatus(r, 200)
        self.assertEqual(g._rate_limit_info.remaining, 1)
        r = go()
        time.sleep(0.1)  # Make sure cache is caught up
        self.assertStatus(r, 429)
        self.assertEqual(g._rate_limit_info.remaining, 0)

        # Wait until the ratelimit has expired, then try again.
        time.sleep(5)
        r = go()
        self.assertStatus(r, 200)
        self.assertEqual(g._rate_limit_info.remaining, 2)

    def test_user_ratelimit(self):
        """
        Set the user's ratelimit_level to a value and confirm that
        """
        user_manipulator.update(self.user, ratelimit_level=10)

        r = self.open('GET', '/test_webservice/LOW_RATE_LIMIT')
        self.assertStatus(r, 200)
        self.assertEqual(
            g._rate_limit_info.remaining,
            self.user.ratelimit_level*3 - 1,
        )

    def test_adsws_user_header(self):
        """
        Test that the correct 'adsws-user' header is passed to remote
        services
        """
        r = self.open('GET', '/test_webservice/ECHO_HEADERS')
        self.assertIn('X-Adsws-Uid', r.json)
        self.assertEqual(self.user.id, int(r.json['X-Adsws-Uid']))

    def test_adsws_user_ratelimit_header(self):
        """
        Test that the correct 'adsws-user_ratelimit_level' header is passed to
        remote services
        """
        r = self.open('GET', '/test_webservice/ECHO_HEADERS')
        self.assertNotIn('X-Adsws-Ratelimit-Level', r.json)

        user_manipulator.update(self.user, ratelimit_level=10)
        r = self.open('GET', '/test_webservice/ECHO_HEADERS')
        self.assertEqual('10', r.json['X-Adsws-Ratelimit-Level'])


class DiscoverLocalModuleTestCase(ApiTestCase, DiscovererTestCase):
    """
    create the discoverer app, adding that a local module's routes to it.
    test that the api/discoverer has these routes, and that they return the
    expected data

    subclass ApiTestCase to ensure self.token (oauth2token) is available for
    the tests
    """
    def create_app(self):
        app = api.create_app(
            WEBSERVICES={
                'adsws.tests.sample_microservice.app': '/test_webservice'
            },
            WEBSERVICES_PUBLISH_ENDPOINT='resources',
            SQLALCHEMY_BINDS=None,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            WTF_CSRF_ENABLED=False,
            TESTING=False,
            DEBUG=False,
            SITE_SECURE_URL='http://localhost',
            SECURITY_POST_LOGIN_VIEW='/postlogin',
            SECURITY_REGISTER_BLUEPRINT=True,
            SHOULD_NOT_OVERRIDE="parent",
            RATELIMITER_KEY_PREFIX='unittest.LocalDiscoverer.{}'.format(
                time.time()),
        )
        return app

    def test_app_config(self):
        """
        Test that that sample application's config is integrated into the api,
        and that config already defined in the api has not been overwritten by
        the sample app
        """

        # This config value should be the parent's
        self.assertEqual(current_app.config['SHOULD_NOT_OVERRIDE'], 'parent')

        # This config value should be the local apps
        self.assertEqual(current_app.config['TEST_SPECIFIC_CONFIG'], 'foo')


class DiscoverRemoteServerTestCase(ApiTestCase, DiscovererTestCase):
    """
    . Run a third party service (webserver via subprocess)
    . create discoverer app, connecting to the service
    . Test that the app has the bootstrapped routes
    . Test GET, POST to the bootstrapped routes -> Backend services response
    . Requires that the remote service be a liveserver with >1 worker
        (https://github.com/adsabs/adsws/issues/19)
    """

    def create_app(self):
        app = api.create_app(
            WEBSERVICES={'http://localhost:5005/': '/test_webservice'},
            WEBSERVICES_PUBLISH_ENDPOINT='resources',
            SQLALCHEMY_BINDS=None,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            WTF_CSRF_ENABLED=False,
            TESTING=False,
            DEBUG=False,
            SITE_SECURE_URL='http://localhost',
            SECURITY_POST_LOGIN_VIEW='/postlogin',
            SECURITY_REGISTER_BLUEPRINT=True,
            SHOULD_NOT_OVERRIDE='parent',
            RATELIMITER_KEY_PREFIX='unittest.LocalDiscoverer.{}'.format(
                time.time()),
        )
        return app

    @classmethod
    def setUpClass(cls):
        cls.setupRemoteServer()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownRemoteServer()

    def test_app_config(self):
        """
        Test that that sample application's config is integrated into the api,
        and that config already defined in the api has not been overwritten by
        the sample app
        """

        # This config value should be the parent's
        self.assertEqual(current_app.config['SHOULD_NOT_OVERRIDE'], 'parent')

        # The remote service should have a completely isolated config
        self.assertNotIn('TEST_SPECIFIC_CONFIG', current_app.config)


class DiscoverConsulServiceTestCase(ApiTestCase, DiscovererTestCase):
    """
    Identifing a service using the 'consul://' prefix should result in that
    service being discovered and bootstrapped into the api
    """

    @classmethod
    def setUpClass(cls):
        cls.patcher_resolve = mock.patch(
            'flask.ext.consulate.ConsulService._resolve'
        )
        mocked_resolve = cls.patcher_resolve.start()
        mocked_resolve.return_value = ["http://localhost:5005"]
        cls.patcher_set_ns = mock.patch(
            'flask.ext.consulate.ConsulService.set_ns'
        )
        mocked_set_ns = cls.patcher_set_ns.start()
        mocked_set_ns.return_value = ["10.1.1.1"]
        cls.setupRemoteServer()

    @classmethod
    def tearDownClass(cls):
        cls.patcher_resolve.stop()
        cls.patcher_set_ns.stop()
        cls.tearDownRemoteServer()

    def create_app(self):
        app = api.create_app(
            WEBSERVICES={'consul://test_webservice.service': '/test_webservice'},
            WEBSERVICES_PUBLISH_ENDPOINT='resources',
            SQLALCHEMY_BINDS=None,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            WTF_CSRF_ENABLED=False,
            TESTING=False,
            DEBUG=False,
            SITE_SECURE_URL='http://localhost',
            SECURITY_POST_LOGIN_VIEW='/postlogin',
            SECURITY_REGISTER_BLUEPRINT=True,
            SHOULD_NOT_OVERRIDE='parent',
            RATELIMITER_KEY_PREFIX='unittest.LocalDiscoverer.{}'.format(
                time.time()),
        )
        return app