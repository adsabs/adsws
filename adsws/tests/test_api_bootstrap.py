from adsws.core import user_manipulator
from adsws.tests.api_base import ApiTestCase
from flask import current_app, url_for
from adsws.testsuite import make_test_suite, run_test_suite
import json
from adsws import api

class TestBootstrap(ApiTestCase):
    
    def create_app(self):
        app = api.create_app(
                SQLALCHEMY_BINDS=None,
                SQLALCHEMY_DATABASE_URI='sqlite://',
                WTF_CSRF_ENABLED = False,
                TESTING = False,
                SITE_SECURE_URL='http://localhost',
                SECURITY_POST_LOGIN_VIEW='/postlogin',
                WEBSERVICES = {},
                SECURITY_REGISTER_BLUEPRINT=True,
                )
        return app

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
            self.assertIn(k,data,msg="{k} not in {data}".format(k=k,data=data))
            self.assertIsNotNone(data[k],msg="data[\"{k}\"] is None".format(k=k))
        self.assertEqual(username,data['username'])

        r = self.client.get(url_for('protectedview'),headers={"Authorization": "Bearer %s" % data['access_token']})
        self.assertStatus(r,200)

TESTSUITE = make_test_suite(TestBootstrap)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)