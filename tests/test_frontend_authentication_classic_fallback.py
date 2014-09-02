
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite,\
    unittest
from flask import Flask, session, url_for
from adsws import frontend
from adsws.core import user_manipulator, db, User
from flask_login import current_user
from mock import MagicMock, patch

class LoginTestCase(FlaskAppTestCase):
    ''' Tests for results of the login_user function '''

    def create_app(self):
        app = frontend.create_app(
                SQLALCHEMY_DATABASE_URI='sqlite://',
                WTF_CSRF_ENABLED = False,
                TESTING = True,
                SECURITY_POST_LOGIN_VIEW='/username',
                FALL_BACK_ADS_CLASSIC_LOGIN=True
                )
        
        @app.route('/username')
        def username():
            if current_user.is_authenticated():
                return current_user.email
            return u'Anonymous'

        @app.errorhandler(404)
        def handle_404(e):
            raise e

        db.create_all(app=app)
        return app
      
    def setUp(self):
        FlaskAppTestCase.setUp(self)
        
        user_manipulator.create(email='admin', password='admin', active=True)
        user_manipulator.create(email='villain', password='villain', active=True)
        user_manipulator.create(email='client', password='client', active=True)
        


    def test_test_request_context_users_are_anonymous(self):
        with self.app.test_request_context():
            self.assertTrue(current_user.is_anonymous())

    def test_defaults_anonymous(self):
        with self.app.test_client() as c:
            result = c.get('/username')
            self.assertEqual(u'Anonymous', result.data.decode('utf-8'))


    def test_normal_login(self):
        u = self.login('admin', 'admin')
        self.assertEqual(u.data, 'admin')
        
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "roman.chyla@gmail.com",
      "cookie": "50eefa48dc",
      "tmp_cookie": "",
      "openurl_srv": "",
      "openurl_icon": "",
      "loggedin": "1",
      "myadsid": "352401271",
      "lastname": "",
      "firstname": "",
      "fullname": "",
      "message": "LOGGED_IN",
      "request": {
          "man_cookie": "",
          "man_email": "roman.chyla@gmail.com",
          "man_nemail": "",
          "man_passwd": "******",
          "man_npasswd": "",
          "man_vpasswd": "",
          "man_name": "",
          "man_url": "http://adsabs.harvard.edu",
          "man_cmd": "4"
       }
    }
    ))
    def test_login_through_classic(self):
        # user does not exist yet
        u = self.login('classic', 'classic')
        self.assertEqual(u.data, 'classic')
        
    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "",
      "cookie": "54050f19fa",
      "tmp_cookie": "",
      "openurl_srv": "",
      "openurl_icon": "",
      "loggedin": "0",
      "myadsid": "0",
      "lastname": "",
      "firstname": "",
      "fullname": "",
      "message": "ACCOUNT_NOTFOUND",
      "request": {
          "man_cookie": "",
          "man_email": "roman.chyla@gmail.comssssss",
          "man_nemail": "",
          "man_passwd": "******",
          "man_npasswd": "",
          "man_vpasswd": "",
          "man_name": "",
          "man_url": "",
          "man_cmd": "4"
       }
    }
    ))
    @unittest.expectedFailure
    def test_login_unknown_user(self):
        u = self.login('classic', 'classic')
        
    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "roman.chyla@gmail.com",
      "cookie": "50eefa48dc",
      "tmp_cookie": "",
      "openurl_srv": "",
      "openurl_icon": "",
      "loggedin": "0",
      "myadsid": "352401271",
      "lastname": "",
      "firstname": "",
      "fullname": "",
      "message": "WRONG_PASSWORD",
      "request": {
          "man_cookie": "",
          "man_email": "roman.chyla@gmail.com",
          "man_nemail": "",
          "man_passwd": "********",
          "man_npasswd": "",
          "man_vpasswd": "",
          "man_name": "",
          "man_url": "",
          "man_cmd": "4"
       }
    }
    ))
    @unittest.expectedFailure
    def test_login_wrong_password(self):
        u = self.login('classic', 'classic')

TESTSUITE = make_test_suite(LoginTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
