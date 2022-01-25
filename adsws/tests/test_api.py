from adsws.testsuite import make_test_suite, run_test_suite
from adsws.core import user_manipulator, db
from .api_base import ApiTestCase as _APITestCase
from adsws import api
from flask import url_for
import time
import testing.postgresql

class ApiTestCase(_APITestCase):
    """
    Tests adsws-API specific endpoints
    """
    postgresql_url_dict = {
        'port': 15678,
        'host': '127.0.0.1',
        'user': 'postgres',
        'database': 'test'
    }
    postgresql_url = 'postgresql://{user}@{host}:{port}/{database}' \
        .format(
        user=postgresql_url_dict['user'],
        host=postgresql_url_dict['host'],
        port=postgresql_url_dict['port'],
        database=postgresql_url_dict['database']
    )

    @classmethod
    def setUpClass(cls):
        cls.postgresql = \
            testing.postgresql.Postgresql(**cls.postgresql_url_dict)

    @classmethod
    def tearDownClass(cls):
        cls.postgresql.stop()

    def create_app(self):
        app = api.create_app(
            WEBSERVICES={},
            SQLALCHEMY_BINDS=None,
            SQLALCHEMY_DATABASE_URI=self.postgresql_url,
            WTF_CSRF_ENABLED=False,
            TESTING=False,
            DEBUG=False,
            SITE_SECURE_URL='http://localhost',
            SECURITY_POST_LOGIN_VIEW='/postlogin',
            SECURITY_REGISTER_BLUEPRINT=True,
            SHOULD_NOT_OVERRIDE="parent",
            RATELIMIT_KEY_PREFIX='unittest.LocalDiscoverer.{}'.format(
                time.time()),
        )
        return app

    def setUp(self):
        engine = db.get_engine(self.app)
        engine.execute('CREATE EXTENSION IF NOT EXISTS citext')
        super(self.__class__, self).setUp()

        # Create a test user that will be queried for
        u = user_manipulator.create(email="test@unittest")
        self.user_email = u.email
        self.user_id = u.id



    def tearDown(self):
        super(self.__class__, self).tearDown()
        db.session.remove()
        db.drop_all(app=self.app)

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

    def test_protected_view(self):
        """
        Test that the route decorated with empty oauth returns 200
        """

        r = self.open('GET', url_for('protectedview'))
        self.assertStatus(r, 200)

    def test_emailresolver(self):
        """
        Test that the email resolver correctly resolves a user
        """

        # Passing the uid should return the correct email
        r = self.open('GET', url_for('userresolver', identifier=self.user_id))
        self.assertEqual(r.json['email'], self.user_email)

        # Passing the email should return the correct uid
        r = self.open('GET', url_for('userresolver', identifier=self.user_email))
        self.assertEqual(r.json['id'], self.user_id)

        # Test case insensitivity on email
        r = self.open('GET', url_for('userresolver', identifier=self.user_email.upper()))
        self.assertEqual(r.json['id'], self.user_id)


TESTSUITE = make_test_suite(
    ApiTestCase,
)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
