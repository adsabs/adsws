from flask import Flask, session, url_for, request, jsonify, Blueprint, current_app
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
from api_base import ApiTestCase, create_client
from adsws import api
import requests
import subprocess
# import httpretty
import os
import json
import time
from stubdata_liveserver import Stubdata


class DiscoverRemoteServerTestCase(ApiTestCase):
  '''
  . Spin up a third party service (actual webserver), including a /resources endpoint
  . create discoverer app, connecting to the service
  . Test that the app has the bootstrapped routes
  . Test GET, POST to the bootstrapped routes -> Backend services response
  '''
  def create_app(self):
    self.setupRemoteServer()
    app = api.create_app(
      WEBSERVICES = {'http://localhost:5005/': '/test_webservice'},
      WEBSERVICES_PUBLISH_ENDPOINT='resources',
      SQLALCHEMY_BINDS=None,
      SQLALCHEMY_DATABASE_URI='sqlite://',
      WTF_CSRF_ENABLED = False,
      TESTING = False,
      SITE_SECURE_URL='http://localhost',
      SECURITY_POST_LOGIN_VIEW='/postlogin',
      )
    self.tearDownRemoteServer()
    return app

  def setupRemoteServer(self):
    path = os.path.join(os.path.dirname(__file__),'stubdata_liveserver','app.py')
    self.liveserver = subprocess.Popen(['python',path])
    time.sleep(1)
  
  def tearDownRemoteServer(self):
    self.liveserver.kill()
    time.sleep(1)

  def setUp(self):
    self.setupRemoteServer()
    super(DiscoverRemoteServerTestCase,self).setUp()

  def tearDown(self):
    self.tearDownRemoteServer()
    super(DiscoverRemoteServerTestCase,self).tearDown()

  def open(self,method,url):
    #return self.client.open(url,method=method)
    return self.client.open(url,method=method,headers={"Authorization": "Bearer %s" % self.token})

  def test_status_route(self):
    r = self.open('GET','/status')
    self.assertStatus(r,200)

  def test_protected_route(self):
    r = self.open('GET','/protected')
    self.assertStatus(r,200)

  def test_resources_route(self):
    r = self.open('GET','/test_webservice/resources')
    self.assertEqual(r.json,Stubdata.resources_route)

  def test_GET_resc(self):
    r = self.open('GET','/test_webservice/GET')
    self.assertEqual(r.json,Stubdata.GET)

    r = self.open('POST','/test_webservice/GET')
    self.assertStatus(r,405) #Expect to get 405 METHOD NOT ALLOWED

  def test_POST_resc(self):
    r = self.open('POST','/test_webservice/POST')
    self.assertEqual(r.json,Stubdata.POST)

    r = self.open('GET','/test_webservice/POST')
    self.assertStatus(r,405) #Expect to get 405 METHOD NOT ALLOWED

  def test_GETPOST_resc(self):
    r = requests.get("http://localhost:5005/GETPOST")
    self.assertEqual(r.json(),Stubdata.GETPOST['GET'])

    r = requests.post("http://localhost:5005/GETPOST")
    self.assertEqual(r.json(),Stubdata.GETPOST['POST'])

    r = self.open('POST','/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['POST'])

    r = self.open('GET','/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['GET'])

  def test_SCOPED(self):
    r = self.open('GET','/test_webservice/SCOPED')
    self.assertStatus(r,401)

TESTSUITE = make_test_suite(DiscoverRemoteServerTestCase)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
