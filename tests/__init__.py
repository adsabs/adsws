# -*- coding: utf-8 -*-
"""
    tests
    ~~~~~

    tests package
"""

from unittest import TestCase

from .utils import FlaskTestCaseMixin


class WebapiTestCase(TestCase):
    pass


class WebapiAppTestCase(FlaskTestCaseMixin, WebapiTestCase):

    def _create_app(self):
        raise NotImplementedError

    def _create_fixtures(self):
        self.user = {}

    def setUp(self):
        super(WebapiTestCase, self).setUp()
        self.app = self._create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        #db.create_all()
        self._create_fixtures()
        self._create_csrf_token()

    def tearDown(self):
        super(WebapiTestCase, self).tearDown()
        #db.drop_all()
        self.app_context.pop()

    def _login(self, email=None, password=None):
        email = email or self.user.email
        password = password or 'password'
        return self.post('/login', data={'email': email, 'password': password},
                         follow_redirects=False)
