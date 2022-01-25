from adsws.core import db
from adsws.testsuite import make_test_suite, run_test_suite
from adsws import api

from flask import current_app
from flask_testing import TestCase


class ApiCORSTestCase(TestCase):
    """Verify that the API handles CORS in the desired manner"""

    def setUp(self):
        db.create_all(app=self.app)

    def tearDown(self):
        db.drop_all(app=self.app)

    def create_app(self):
        app = api.create_app(
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_BINDS=None,
            CORS_DOMAINS=['http://localhost', 'localhost:5000', 'localhost'],
            CORS_HEADERS=['content-type', 'X-BB-Api-Client-Version',
                          'Authorization', 'Accept', 'foo'],
            CORS_METHODS=['GET', 'OPTIONS', 'POST', 'PUT'],
            WEBSERVICES={},
            )
        return app

    def compare_headers(self, header, _list):
        """
        Utility function that parses headers into a list, and asserts that
        that parsed list if equal to an input list

        :param header: Raw string header
        :param _list: List to comapre against, after parsing the header
        :return: Exception or None
        """
        if isinstance(header, str):
            header = [i.strip() for i in header.split(',')]
        self.assertItemsEqual(header, _list)

    def test_allow_origin(self):
        """
        Ensure that response headers have the correct CORS_DOMAINS
        """

        r = self.client.get('/status', headers=None)
        self.assertStatus(r, 200)
        self.compare_headers(
            r.headers.get('Access-Control-Allow-Origin'),
            current_app.config['CORS_DOMAINS'],
        )

        for origin in ['http://localhost', 'localhost:5000', 'localhost']:
            r = self.client.get('/status', headers={'Origin': origin})
            self.assertStatus(r, 200)
            self.assertIn(origin, r.headers.get('Access-Control-Allow-Origin'))

    def test_options(self):
        """
        responses to the http OPTIONS method should return info about the
        server's CORS configuration
        """
        r = self.client.options(
            '/status',
            headers={
                'Origin': 'http://localhost',
                'Access-Control-Request-Method': 'OPTIONS',
                'Access-Control-Request-Headers': 'accept, '
                                                  'x-bb-api-client-version, '
                                                  'content-type'
            }
        )
        self.assertIn('Access-Control-Allow-Methods', r.headers)
        self.assertIn('Access-Control-Allow-Headers', r.headers)

        self.compare_headers(
            r.headers['Access-Control-Allow-Methods'],
            current_app.config['CORS_METHODS']
        )
        self.compare_headers(
            r.headers['Access-Control-Allow-Headers'],
            current_app.config['CORS_HEADERS']
        )
        
        
TESTSUITE = make_test_suite(ApiCORSTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
