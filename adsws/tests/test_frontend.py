from flask.ext.testing import TestCase
from unittest import TestCase as UnitTestCase
from flask import current_app, url_for, session

from adsws.testsuite import make_test_suite, run_test_suite

from adsws import frontend

class TestFrontend(TestCase):
  '''Test the accounts API'''

  def create_app(self):
    app = frontend.create_app()
    return app

  def test_statusView(self):
    url = url_for('statusview')
    r = self.client.get(url)
    self.assertStatus(r,200)
    self.assertEqual(r.json['status'],'online')

TESTSUITE = make_test_suite(TestFrontend)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
