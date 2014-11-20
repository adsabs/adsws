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
        
    def test_race_condition(self):
        from adsws.api.models import OAuthClientLimits
        from adsws.core import db
        
        c1 = OAuthClientLimits(client_id=1)
        c2 = OAuthClientLimits(client_id=1)
        
        c1.counter = 1
        db.session.add(c1)
        db.session.commit()
        db.session.expunge(c1)
        
        c2.increase()
        self.assertEqual(c2.counter, 2);

TESTSUITE = make_test_suite(TestApiLimits)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)