from flask.ext.testing import TestCase
from unittest import TestCase as UnitTestCase
from unittest import skip
from flask.ext.login import current_user
from flask.ext.mail import Message
from flask import current_app, url_for, session

from adsws.core import db, user_manipulator
from adsws.testsuite import make_test_suite, run_test_suite
import json

from adsws import accounts
from adsws.accounts import utils
from adsws.accounts.emails import PASSWORD_RESET_EMAIL, VERIFICATION_EMAIL

import httpretty
import requests
import datetime

class TestUtils(UnitTestCase):
  '''Test account validation utilities'''

  def test_get_post_data(self):
    class FakeRequest: pass
    request = FakeRequest()
    request.values = "format=form"
    request.get_json = lambda **x: {'format':'json'}
    
    #empty content-type -> default to json
    data = utils.get_post_data(request)
    self.assertEqual(data,request.get_json())

    request.get_json = lambda **x: {}.method() #raise some exception when it tries to run get_json(force=true)
    data = utils.get_post_data(request)
    self.assertEqual(data,request.values)

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
    app = accounts.create_app(
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
      SECRET_KEY="unittests-secret-key",
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
      data = request.parsed_body
      if data['response'][0] == 'correct_response':
        res = {'success':True}
      elif data['response'][0] == 'incorrect_response':
        res = {'success':False}
      elif data['response'][0] == 'dont_return_200':
        return (503,headers,"Service Unavailable")
      else:
        raise Exception("This case is not expected by the tests: %s" % qs)
      return (200,headers,json.dumps(res))
    httpretty.register_uri(httpretty.POST, url, body=callback,content_type='application/json')

  def test_401_no_challenge(self):
    '''
    Test that a 401 response does not include a WWW-Authenticate header, which the browser
    will respond to by opening a login prompt
    '''
    urls = [url_for(i) for i in ['protectedview','userauthview']]
    for url in urls:
      r = self.client.get(url)
      self.assertNotIn('WWW-Authenticate',r.headers,msg='challenge issued on %s' % url)
  
  def test_delete_account(self):
    url = url_for('deleteaccountview')
    with self.client as c:
      csrf = self.get_csrf()

      #CSRF not specified
      r = c.post(url)
      self.assertStatus(r,400)

      #/delete when not authenticated
      r = c.post(url,headers={'X-CSRFToken':csrf})
      self.assertStatus(r,401)

      #login
      user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())
      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      c.post(url_for('userauthview'),data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})

      r = c.post(url,headers={'X-CSRFToken':csrf})
      self.assertStatus(r,200)

      u = user_manipulator.first(email=self.REAL_USER_EMAIL)
      self.assertIsNone(u)

  def test_adsapi_token_workflow(self):
    url = url_for('personaltokenview')
    with self.client as c:
      csrf = self.get_csrf()

      #User must be authenticated
      r = c.get(url)
      self.assertStatus(r,401)

      #login
      user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())
      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      c.post(url_for('userauthview'),data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      
      #no api client has yet been registered.
      r = c.get(url)
      self.assertEqual(r.json['message'],'no ADS API client found')

      #POST to make the API client, but no CSRF token passed
      r = c.post(url)
      self.assertStatus(r,400)

      #POST to make the API client
      r = c.post(url,headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,200)
      self.assertIn('access_token',r.json)
      tok = r.json['access_token']

      #GET should return the same access token
      r = c.get(url)
      self.assertEqual(tok,r.json['access_token'])

      #POST should generate a new access_token
      r = c.post(url,headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertNotEqual(tok,r.json['access_token'])
      tok2 = r.json['access_token']
      self.assertNotEqual(tok,tok2)

      #GET should return the updated token
      r = c.get(url)
      self.assertEqual(tok2,r.json['access_token'])

  def test_change_email(self):
    '''
    Test the change email workflow
    '''
    url = url_for('changeemailview')
    with self.client as c:
      csrf = self.get_csrf()
      self.setup_google_recaptcha_response()
      u = user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())
      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      r = c.post(url_for('userauthview'),data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,200)

      #incorrect password, even though we're logged in
      payload = {'email':self.REAL_USER_EMAIL,'password':'not_correct','verify_url':'http://not_relevant.com'}
      r = c.post(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,401)

      #correct password, but user already exists
      payload = {'email':self.REAL_USER_EMAIL,'password':'user','verify_url':'http://not_relevant.com'}
      r = c.post(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,403)

      #correct
      payload = {'email':'changed@email','password':'user','verify_url':'http://not_relevant.com'}
      r = c.post(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,200)

      u = user_manipulator.first(email='changed@email')
      self.assertIsNotNone(u)
      self.assertIsNone(u.confirmed_at)
      self.assertIsNone(user_manipulator.first(email=self.REAL_USER_EMAIL))

  def test_reset_password(self):
    '''
    Test reset password workflow
    '''
    with self.client as c:
      csrf = self.get_csrf()
      self.setup_google_recaptcha_response()
      user_manipulator.update(self.real_user,confirmed_at=datetime.datetime.now())

      url = url_for('forgotpasswordview',token="this_email_wasnt@registered")
      payload = {'g-recaptcha-response':'correct_response','reset_url':'http://not_relevant.com'}
      
      #Attempt to reset the password for an unregistered email address
      r = c.post(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,404)
      self.assertEqual(r.json['error'],'no such user exists')

      #Resetting password for the default user is not permitted
      url = url_for('forgotpasswordview',token=self.BOOTSTRAP_USER_EMAIL)
      r = c.post(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,403)

      #This is the proper request
      url = url_for('forgotpasswordview',token=self.REAL_USER_EMAIL)
      r = c.post(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,200)
      self.assertEqual(r.json['message'],'success')

      #Now let's test GET and PUT requests with the encoded token
      msg, token = utils.send_email(self.REAL_USER_EMAIL,'localhost',PASSWORD_RESET_EMAIL, self.REAL_USER_EMAIL)
      url = url_for('forgotpasswordview',token=token)

      #Test de-coding and verifying of the token
      r = c.get(url)
      self.assertStatus(r,200)
      self.assertEqual(r.json['email'],self.REAL_USER_EMAIL)

      payload = {'password1':'123Abc','password2':'123Abc'}
      r = c.put(url,data=json.dumps(payload),headers={'X-CSRFToken':csrf,'content-type':'application/json'})
      self.assertStatus(r,200)
      self.assertEqual(r.json['message'],'success')

      url = url_for('userauthview')
      payload = {'username':self.REAL_USER_EMAIL,'password':'123Abc'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf}) 
      self.assertStatus(r,200)      
      self.assertEqual(current_user.email, self.REAL_USER_EMAIL)


  def test_verification_email(self):
    '''
    Test encoding an email, and see if it 
    can be resolved with the verify endpoint
    '''

    msg, token = utils.send_email("this_email_wasnt@registered",'localhost',VERIFICATION_EMAIL, "this_email_wasnt@registered")
    self.assertIn("localhost",msg.html)

    url = url_for('verifyemailview',token=token)

    #Even though we have a token, no user was registered. This should not
    #actually happen in normal use.
    r = self.client.get(url)
    self.assertStatus(r,404)
    self.assertEqual(r.json['error'],"no user associated with that verification token")

    #Test for an inproperly encoded email, expect 404
    r = self.client.get(url+"incorrect")
    self.assertStatus(r,404)
    self.assertEqual(r.json['error'],'unknown verification token')

    msg, token = utils.send_email(self.REAL_USER_EMAIL,'localhost',VERIFICATION_EMAIL,self.REAL_USER_EMAIL)
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

    self.setup_google_recaptcha_response()

    #Set up a fake request object that will be passed directly to the function
    class FakeRequest:  pass
    fakerequest = FakeRequest()
    fakerequest.remote_addr = 'placeholder'
    
    #Test a "success" response
    fakerequest.get_json = lambda **x: {'g-recaptcha-response':'correct_response'}
    res = utils.verify_recaptcha(fakerequest)
    self.assertTrue(res)

    #Test a "fail" response
    fakerequest.get_json = lambda **x: {'g-recaptcha-response':'incorrect_response'}
    res = utils.verify_recaptcha(fakerequest)
    self.assertFalse(res)

    #Test a 503 response
    fakerequest.get_json = lambda **x: {'g-recaptcha-response':'dont_return_200'}
    self.assertRaises(requests.HTTPError,utils.verify_recaptcha,fakerequest)

    #Test a malformed request
    fakerequest = FakeRequest()
    self.assertRaises((KeyError,AttributeError),utils.verify_recaptcha,fakerequest)


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
      self.assertEqual(r.json['error'],'account has not been verified')

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

  def test_bootstrap_bumblebee(self):
    url = url_for('bootstrap')
    with self.client as c:
      r = c.get(url)
      self.assertEqual(r.json['username'],self.BOOTSTRAP_USER_EMAIL)
      
      #Now manually expire the token
      from adsws.modules.oauth2server.models import OAuthToken
      tok = db.session.query(OAuthToken).filter_by(access_token=r.json['access_token']).one()
      tok.expires = datetime.datetime.now()
      db.session.commit()

      # re-visit the bootstrap URL, test to see if we get a fresh token
      r = c.get(url)
      self.assertNotEqual(r.json['access_token'],tok.access_token)

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
      self.assertEqual(r.json['scopes'],current_app.config['USER_DEFAULT_SCOPES'])

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
      payload = {'old_password':'user','new_password2':'123Abc','new_password1':'123Abc'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,200)
      self.assertEqual(r.json['message'],'success')

      #test that the new login works
      c.get(url_for('logoutview'))
      payload = {'username':self.REAL_USER_EMAIL,'password':'123Abc'}
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
      payload = {'email':'me@email','password1':'Password1','password2':'Password1','g-recaptcha-response':'correct_response','verify_url':'http://not_relevant.com'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,200)
      self.assertEqual(r.json['message'],'success')

      #Test that re-registering the previously registered user fails
      payload = {'email':'me@email','password1':'Password1','password2':'Password1','g-recaptcha-response':'correct_response','verify_url':'http://not_relevant.com'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf})
      self.assertStatus(r,409)
      self.assertIn('error',r.json)


TESTSUITE = make_test_suite(TestAccounts, TestUtils)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
