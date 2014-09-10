# -*- coding: utf-8 -*-
"""
    tests
    ~~~~~

    tests package
"""

from __future__ import print_function, with_statement

# pylint: disable=E1102

CFG_TESTUTILS_VERBOSE = 1

import os
import sys
import time
# Flask-Testing is doing it this way (so we must follow)
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from six import iteritems
from adsws.factory import create_app
    
from unittest import TestCase
from .utils import FlaskTestCaseMixin
from flask.ext.testing import TestCase as FlaskTestCase

from flask import url_for

nottest = unittest.skip('nottest')



def run_test_suite(testsuite):
    """"Run given testsuite.

    Convenience function to embed in test suites.
    """
    runner = unittest.TextTestRunner(descriptions=False, verbosity=2)
    return runner.run(testsuite).wasSuccessful()

def make_test_suite(*test_cases):
    """Build up a test suite given separate test cases."""
    return unittest.TestSuite([unittest.makeSuite(case, 'test')
                               for case in test_cases])


class FlaskAppTestCase(FlaskTestCase):
    """Base test case for AdsWS Flask apps."""

    @property
    def config(self):
        return self._config 
    
    def __init__(self, *args, **kwargs):
        self._config = {
            'SQLALCHEMY_DATABASE_URI' : 'sqlite://'
        }
        super(FlaskTestCase, self).__init__(*args, **kwargs)
        

    def create_app(self):
        """Create the Flask application for testing."""
        app = create_app(**self.config)
        app.testing = True
        return app

    def login(self, username, password):
        """Log in as username and password."""
        r = self.client.post('/login',
                                base_url=self.app.config.get('SITE_SECURE_URL'),
                                #rewrite_to_secure_url(request.base_url),
                                data=dict(email=username,
                                          password=password),
                                follow_redirects=False)
        self.assertTrue('/login' not in r.location)
        #self.assertTrue('<form action="/login"' not in r.data)
        return r

    def logout(self):
        """Log out."""
        r = self.client.get('/logout',
                               base_url=self.app.config.get('SITE_SECURE_URL'),
                               follow_redirects=False)
        self.assertTrue('/logout' not in r.location)
        #self.assertTrue('<form action="/logout"' not in r.data)
        return r

    def shortDescription(self):
        """Return a short description of the test case."""
        return
    
class AdsWSTestCase(TestCase):
    pass


class AdsWSAppTestCase(FlaskTestCaseMixin, AdsWSTestCase):

    def _create_app(self):
        raise NotImplementedError

    def _create_fixtures(self):
        self.user = {}

    def setUp(self):
        super(AdsWSTestCase, self).setUp()
        self.app = self._create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        #db.create_all()
        self._create_fixtures()
        self._create_csrf_token()

    def tearDown(self):
        super(AdsWSTestCase, self).tearDown()
        #db.drop_all()
        self.app_context.pop()

    def _login(self, email=None, password=None):
        email = email or self.user.email
        password = password or 'password'
        return self.post('/login', data={'email': email, 'password': password},
                         follow_redirects=False)
