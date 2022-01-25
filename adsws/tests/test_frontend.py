from flask_testing import TestCase
from flask import url_for

from adsws.testsuite import make_test_suite, run_test_suite
from adsws import frontend

class TestFrontend(TestCase):
    """
    Test the root application
    """

    def create_app(self):
        app = frontend.create_app(resources={'foo': 'bar'})
        return app

    def test_statusView(self):
        url = url_for('statusview')
        r = self.client.get(url)
        self.assertStatus(r, 200)
        self.assertEqual(r.json['status'], 'online')

    def test_globalresources(self):
        url = url_for('globalresourcesview')
        r = self.client.get(url)
        self.assertStatus(r, 200)
        self.assertEqual(r.json['foo'], 'bar')

TESTSUITE = make_test_suite(TestFrontend)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
