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
pyv = sys.version_info
if pyv[0] == 2 and pyv[1] < 7:
    import unittest2 as unittest
else:
    import unittest
    
from unittest import TestCase

from .utils import FlaskTestCaseMixin

from flask.ext.testing import TestCase

nottest = unittest.skip('nottest')

@nottest
def run_test_suite(testsuite, warn_user=False):
    """"Run given testsuite.

    Convenience function to embed in test suites.
    """
    runner = unittest.TextTestRunner(descriptions=False, verbosity=2)
    return runner.run(testsuite).wasSuccessful()

def make_test_suite(*test_cases):
    """Build up a test suite given separate test cases."""
    return unittest.TestSuite([unittest.makeSuite(case, 'test')
                               for case in test_cases])
    
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
