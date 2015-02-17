from flask.ext.testing import TestCase
from unittest import TestCase as UnitTestCase
from flask.ext.login import current_user, login_user, logout_user
from flask.ext.mail import Message
from flask import current_app, url_for, session

from adsws.core import db, user_manipulator
from adsws.testsuite import make_test_suite, run_test_suite
import json

from adsws import api
from adsws.api.accounts import utils

import httpretty
import requests
import datetime

class TestUtils(UnitTestCase):
  '''Test account validation utilities'''

  def test_validate_email(self):
    self.assertRaises(utils.ValidationError,utils.validate_email,"invalid email")
    #Minimum validation is that "@" is in the string
    #This is OK since we will verify the email anyways.
    self.assertTrue(utils.validate_email('@')) 
  def test_validate_password(self):
    self.assertRaises(utils.ValidationError,utils.validate_password,"no Numbers")
    self.assertRaises(utils.ValidationError,utils.validate_password,"123456")
    self.assertRaises(utils.ValidationError,utils.validate_password,"2Shrt")
    self.assertRaises(utils.ValidationError,utils.validate_password,"n0 caps")
    self.assertTrue(utils.validate_password("123Aabc"))

class TestAccounts(TestCase):
  '''Test the accounts API'''

  def tearDown(self):
    httpretty.disable()
    httpretty.reset()
    self.bootstrap_user = None
    self.real_user = None

  def create_app(self):
    self.BOOTSTRAP_USER_EMAIL = 'bootstrap@unittests'
    self.REAL_USER_EMAIL = 'user@unittests'
    app = api.create_app(
      SQLALCHEMY_BINDS=None,
      SQLALCHEMY_DATABASE_URI='sqlite://',
      TESTING = False,
      SITE_SECURE_URL='http://localhost',
      WEBSERVICES = {},
      GOOGLE_RECAPTCHA_ENDPOINT = 'http://google.com/verify_recaptcha',
      GOOGLE_RECAPTCHA_PRIVATE_KEY = 'fake_recaptcha_key',
      SECURITY_REGISTER_BLUEPRINT = False,
      BOOTSTRAP_USER_EMAIL = self.BOOTSTRAP_USER_EMAIL,
      MAIL_SUPPRESS_SEND = True,
      )
    db.create_all(app=app)
    return app

  def setUp(self):
    self.bootstrap_user = user_manipulator.create(email=self.BOOTSTRAP_USER_EMAIL, password='bootstrap', active=True)
    self.real_user = user_manipulator.create(email=self.REAL_USER_EMAIL, password='user', active=True)

  def setup_google_recaptcha_response(self):
    '''Set up the mocked google recaptcha api'''
    httpretty.enable()
    url = current_app.config['GOOGLE_RECAPTCHA_ENDPOINT']
    def callback(request, uri, headers):
      qs = request.querystring
      if qs['response'][0] == 'correct_response':
        res = {'success':True}
      elif qs['response'][0] == 'incorrect_response':
        res = {'success':False}
      elif qs['response'][0] == 'dont_return_200':
        return (503,headers,"Service Unavailable")
      else:
        raise Exception("This case is not expected by the tests: %s" % qs)
      return (200,headers,json.dumps(res))
    httpretty.register_uri(httpretty.GET, url, body=callback,content_type='application/json')
  
  def test_verification_email(self):
    '''
    Test encoding an email, and see if it 
    can be resolved with the verify endpoint
    '''

    msg,token = utils.send_verification_email("this_email_wasnt@registered")
    url = url_for('verifyemailview',token=token)

    #Even though we have a token, no user was registered. This should not
    #actually happen in normal user.
    r = self.client.get(url)
    self.assertStatus(r,404)
    self.assertEqual(r.json['error'],"no user associated with that verification token")

    #Test for an inproperly encoded email, expect 404
    r = self.client.get(url+"incorrect")
    self.assertStatus(r,404)
    self.assertEqual(r.json['error'],'unknown verification token')

    msg,token = utils.send_verification_email(self.REAL_USER_EMAIL)
    url = url_for('verifyemailview',token=token)

    #Test a proper verification
    r = self.client.get(url)
    self.assertStatus(r,200)
    self.assertEqual(r.json["email"],self.REAL_USER_EMAIL)

    #Test for an already confirmed email
    r = self.client.get(url)
    self.assertStatus(r,400)
    self.assertEqual(r.json["error"],"this user and email has already been validated")


  def test_verify_google_recaptcha(self):
    '''Test the function responsible for contacting 
    the google recaptcha API and verifying the captcha response'''

    from adsws.api.accounts.utils import verify_recaptcha
    self.setup_google_recaptcha_response()

    #Set up a fake request object that will be passed directly to the function
    class FakeRequest:  pass
    fakerequest = FakeRequest()
    fakerequest.remote_addr = 'placeholder'
    fakerequest.headers = {}
    
    #Test a "success" response
    fakerequest.json = {'g-recaptcha-response':'correct_response'}
    res = verify_recaptcha(fakerequest)
    self.assertTrue(res)

    #Test a "fail" response
    fakerequest.json = {'g-recaptcha-response':'incorrect_response'}
    res = verify_recaptcha(fakerequest)
    self.assertFalse(res)

    #Test a 503 response
    fakerequest.json = {'g-recaptcha-response':'dont_return_200'}
    self.assertRaises(requests.HTTPError,verify_recaptcha,fakerequest)

    #Test a malformed request
    fakerequest = FakeRequest()
    self.assertRaises((KeyError,AttributeError),verify_recaptcha,fakerequest)


  def test_login_and_logout(self):
    url = url_for('userauthview')

    payload = {'username':'foo','password':'bar'}
    r = self.client.post(url,data=json.dumps(payload),headers={'content-type':'application/json'})
    self.assertStatus(r,400) #No csrf token = 400

    with self.client as c:
      r = c.get(url_for('bootstrap'))
      self.assertEqual(r.json['username'],self.BOOTSTRAP_USER_EMAIL)
      self.assertEqual(current_user.email,self.BOOTSTRAP_USER_EMAIL) #This will log the user in as the bootstrap user
      csrf = self.get_csrf()

      #Test disallowed GET when authenticated as BOOTSTRAP_USER
      r = c.get(url)
      self.assertStatus(r,401)

      #Test incorrect login
      payload = {'username':'foo','password':'bar'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf}) 
      self.assertStatus(r,401)
      self.assertEqual(current_user.email, self.BOOTSTRAP_USER_EMAIL)

      #Test correct login, but account has not been verified
      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf}) 
      self.assertStatus(r,403)
      self.assertEqual(r.json['message'],'account has not been verified')

      #Test correct login on a verified account
      user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf}) 
      self.assertStatus(r,200)      
      self.assertEqual(current_user.email, self.REAL_USER_EMAIL)

      #Test logout
      r = c.get(url_for('logoutview'))
      self.assertStatus(r,200)
      self.assertFalse(current_user.is_authenticated())

  def get_csrf(self):
    r = self.client.get(url_for('bootstrap'))
    return r.json['csrf']

  def test_bootstrap_user(self):
    url = url_for('bootstrap')
    with self.client as c:
      csrf = self.get_csrf()

      #log in as real user
      user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())
      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      c.post(url_for('userauthview'),data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})   

      #re-visit bootstrap, make sure you get the user's info
      r = c.get(url)
      self.assertEqual(r.json['username'],self.REAL_USER_EMAIL)
      self.assertEqual(r.json['scopes'],["ads:user:default"])

  def test_change_password(self):
    url = url_for('changepasswordview')
    with self.client as c:
      csrf = self.get_csrf()

      #no csrf token
      r = c.post(url,headers={'content-type':'application/json'})
      self.assertStatus(r,400)

      #test unauthenticated request
      payload = {'old_password':'user','new_password2':'foo','new_password1':'foo'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,401)

      #authenticate
      user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())
      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      r=c.post(url_for('userauthview'),data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})   

      #test authenticated request, but incorrect old_password
      payload = {'old_password':'wrong','new_password2':'foo','new_password1':'foo'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,401)
      self.assertEqual(r.json['error'],'please verify your current password')

      #test authenticated request, but correct old_password
      payload = {'old_password':'user','new_password2':'foo','new_password1':'foo'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,200)
      self.assertEqual(r.json['message'],'success')

      #test that the new login works
      c.get(url_for('logoutview'))
      payload = {'username':self.REAL_USER_EMAIL,'password':'foo'}
      r=c.post(url_for('userauthview'),data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})   
      self.assertStatus(r,200)


  def test_register_user(self):
    url = url_for('userregistrationview')
    with self.client as c:
      csrf = self.get_csrf()

      self.setup_google_recaptcha_response() #httpretty socket blocks if enabled before self.get_csrf() !
      r = c.post(url,headers={'content-type':'application/json'})
      self.assertStatus(r,400) #csrf protected

      #Test giving wrong input
      payload = {'email':'me@email'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,400)
      self.assertIn('error',r.json)

      #Test a valid new user registration
      payload = {'email':'me@email','password1':'Password1','password2':'Password1','g-recaptcha-response':'correct_response'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,200)
      self.assertEqual(r.json['message'],'success')

      #Test that re-registering the previously registered user fails
      payload = {'email':'me@email','password1':'Password1','password2':'Password1','g-recaptcha-response':'correct_response'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,409)
      self.assertIn('error',r.json)


TESTSUITE = make_test_suite(TestAccounts, TestUtils)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)