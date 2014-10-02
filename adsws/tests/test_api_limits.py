from __future__ import absolute_import
from adsws.tests.api_base import ApiTestCase
from flask import url_for
from adsws.testsuite import make_test_suite, run_test_suite
import httpretty
import json
import time
from adsws.api import route, limit_rate
from adsws.modules.oauth2server.provider import oauth2

class TestApiLimits(ApiTestCase):
    
    def create_app(self):
        app = super(TestApiLimits, self).create_app()
    
        @app.route('/test_rate')
        @oauth2.require_oauth('api:search')
        @limit_rate()
        def test_rate():
            return 'OK'
        
        return app
        
    def test_rate(self):
        #self.authenticate()
        self.app.config['MAX_RATE_LIMITS']['default'] = 2
        self.app.config['MAX_RATE_EXPIRES_IN'] = 1
        
        resp = self.remote_client.get(url_for('test_rate'))
        self.assertEqual(resp.status, 200)
        
        resp = self.remote_client.get(url_for('test_rate'))
        self.assertEqual(resp.status, 401)
        
        time.sleep(1)
        
        resp = self.remote_client.get(url_for('test_rate'))
        self.assertEqual(resp.status, 200)
        

TESTSUITE = make_test_suite(TestApiLimits)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)