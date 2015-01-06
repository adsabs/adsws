from adsws.core import user_manipulator
from adsws.tests.api_base import ApiTestCase
from flask import current_app, url_for
from adsws.testsuite import make_test_suite, run_test_suite
import json

class TestBumbleBee(ApiTestCase):
    
    def test_bootstrap_anonymous(self):
        user_manipulator.create(email=current_app.config.get('BOOTSTRAP_USER_EMAIL'), id=-1)
        self.bootstrap('anonymous@adslabs.org')
        
    def test_bootstrap_user(self):
        user_manipulator.create(email='real@adslabs.org', 
                                active=True,
                                password='real')
        self.login('real@adslabs.org', 'real')
        self.bootstrap('real@adslabs.org')
        
    def bootstrap(self,username):
        r = self.client.get(url_for('bootstrap'))
        self.assertTrue(r.status_code, 200)
        data = json.loads(r.data)
        for k in ['access_token','expire_in','scopes','token_type','username','refresh_token']:
            self.assertIn(k,data)
            self.assertIsNotNone(data[k])
        self.assertEqual(username,data['username'])

        r = self.client.get(url_for('protectedview'),headers={"Authorization": "Bearer %s" % data['access_token']})
        self.assertStatus(r,200)

TESTSUITE = make_test_suite(TestBumbleBee)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)