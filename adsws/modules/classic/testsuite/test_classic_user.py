
from adsws.testsuite import FlaskAppTestCase, make_test_suite, \
    run_test_suite, unittest

from adsws.modules.classic.user import ClassicUser, ClassicUserInfo
from mock import MagicMock, patch

from adsws.factory import create_app


class TestClassicUser(FlaskAppTestCase):
    
    def create_app(self):
        app = create_app(__name__)
        app.config['CLASSIC_LOGIN_URL'] = 'http://foo.bar.org/cgi-bin/maint/manage_account/credentials'
        return app
    

    @unittest.expectedFailure    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value=[]))
    def test_load_user_wrong_data(self):
        user = ClassicUserInfo('test@adslabs.org')
        
    @unittest.expectedFailure    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={}))
    def test_load_user_wrong_data2(self):
        user = ClassicUserInfo('test@adslabs.org')
        
    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "test@adslabs.org",
      "cookie": "50eefa48dc",
      "tmp_cookie": "",
      "openurl_srv": "",
      "openurl_icon": "",
      "loggedin": "0",
      "myadsid": "352401271",
      "lastname": "",
      "firstname": "",
      "fullname": "",
      "message": "PASSWORD_REQUIRED",
      "request": {
          "man_cookie": "",
          "man_email": "test@adslabs.org",
          "man_nemail": "",
          "man_passwd": "",
          "man_npasswd": "",
          "man_vpasswd": "",
          "man_name": "",
          "man_url": "",
          "man_cmd": "4"
       }
    }
    ))    
    def test_load_user(self):
        user = ClassicUserInfo('test@adslabs.org')
        self.assertFalse(user.is_authenticated)
        self.assertTrue(user.is_real_user())
        self.assertEqual(352401271, user.get_id())
        self.assertEqual(user.passwd_info(), 0)

    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "test@adslabs.org",
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
          "man_email": "test@adslabs.org",
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
    def test_load_user_using_wrong_password(self):
        user = ClassicUserInfo('test@adslabs.org', 'foo')
        self.assertFalse(user.is_authenticated)
        self.assertTrue(user.is_real_user())
        self.assertEqual(352401271, user.get_id())
        self.assertEqual(user.passwd_info(), -1)
        
    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "",
      "cookie": "5405112700",
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
    def test_load_nonexisting_user(self):
        user = ClassicUserInfo('testx@adslabs.org', 'foo')
        self.assertFalse(user.is_authenticated)
        self.assertFalse(user.is_real_user())
        self.assertEqual(0, user.get_id())
        self.assertEqual(user.passwd_info(), -1)

    
    @patch('adsws.modules.classic.user.user_query', MagicMock(return_value={
      "email": "test@adslabs.org",
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
          "man_email": "test@adslabs.org",
          "man_nemail": "",
          "man_passwd": "******",
          "man_npasswd": "*******",
          "man_vpasswd": "*******",
          "man_name": "",
          "man_url": "http://adsabs.harvard.edu",
          "man_cmd": "4"
       }
    }
    ))    
    def test_update_passwd(self):
        user = ClassicUser('test@adslabs.org', 'foo')
        self.assertTrue(user.is_authenticated)
        self.assertTrue(user.is_real_user())
        self.assertEqual(352401271, user.get_id())
        self.assertEqual(user.passwd_info(), 1)
        
        import adsws.modules.classic.user as x
        
        r = user.update_passwd('test@adslabs.org', 'foobar', 'foobar2')
        x.user_query.assert_called_with(
            {'man_email': 'test@adslabs.org', 
             'man_cmd': 'Update Record', 
             'man_vpasswd': 'foobar2', 
             'man_npasswd': 'foobar2', 
             'man_passwd': 'foobar'}, 
            {'User-Agent': 'ADS Script Request Agent'}, 
            'http://foo.bar.org/cgi-bin/maint/manage_account/credentials')
    


SUITE = make_test_suite(TestClassicUser)

if __name__ == '__main__':
    run_test_suite(SUITE)    