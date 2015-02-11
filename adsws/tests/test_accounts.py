from adsws.tests.api_base import ApiTestCase
from flask.ext.testing import TestCase
from flask.ext.login import current_user
from flask import current_app, url_for, session
from adsws.core import db, user_manipulator
from adsws.testsuite import make_test_suite, run_test_suite
import json
from adsws import api
import httpretty
import requests

class TestAccounts(TestCase):
  '''Test the accounts API'''

  def tearDown(self):
    httpretty.disable()
    httpretty.reset()
    for u in self.users:
      user_manipulator.delete(u)

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
      BOOTSTRAP_USER_EMAIL = self.BOOTSTRAP_USER_EMAIL
      )
    db.create_all(app=app)
    return app

  def setUp(self):
    bootstrap_user = user_manipulator.create(email=self.BOOTSTRAP_USER_EMAIL, password='bootstrap', active=True)
    real_user = user_manipulator.create(email=self.REAL_USER_EMAIL, password='user', active=True)
    self.users = [bootstrap_user,real_user]


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

  def test_verify_google_recaptcha(self):
    '''Test the function responsible for contacting 
    the google recaptcha API and verifying the captcha response'''

    from adsws.api.accounts.views import verify_recaptcha
    self.setup_google_recaptcha_response()

    #Set up a fake request object that will be passed directly to the function
    class FakeRequest:  pass
    fakerequest = FakeRequest()
    fakerequest.remote_addr = 'placeholder'
    
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
      csrf = r.json['csrf']

      payload = {'username':'foo','password':'bar'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf}) 
      self.assertStatus(r,401)
      self.assertEqual(current_user.email, self.BOOTSTRAP_USER_EMAIL)

      payload = {'username':self.REAL_USER_EMAIL,'password':'user'}
      r = c.post(url,data=json.dumps(payload),headers={'content-type':'application/json','X-CSRFToken':csrf}) 
      self.assertStatus(r,200)
      self.assertEqual(current_user.email, self.REAL_USER_EMAIL)

      r = c.get(url_for('logoutview'))
      self.assertStatus(r,200)
      self.assertFalse(current_user.is_authenticated())



TESTSUITE = make_test_suite(TestAccounts)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)