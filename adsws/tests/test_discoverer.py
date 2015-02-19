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
from sample_microservice import Stubdata

LIVESERVER_WAIT_SECONDS = 2.5


class DiscovererTestCase:
  def setupRemoteServer(self):
    path = os.path.join(os.path.dirname(__file__),'sample_microservice','app.py')
    self.liveserver = subprocess.Popen(['python',path])
    time.sleep(LIVESERVER_WAIT_SECONDS)
  
  def tearDownRemoteServer(self):
    self.liveserver.kill()
    time.sleep(LIVESERVER_WAIT_SECONDS)

  def open(self,method,url,**kwargs):
    #return self.client.open(url,method=method)
    return self.client.open(url,method=method,headers={"Authorization": "Bearer %s" % self.token},**kwargs)

class DiscoverLocalModuleTestCase(ApiTestCase,DiscovererTestCase):
  '''
  . Import a local module
  . create the discoverer app, adding that module's routes to the api/discoverer
  . test that the api/discoverer has these routes, and that they return the expected data
  '''
  def create_app(self):
    app=api.create_app(
      WEBSERVICES = {'adsws.tests.sample_microservice.app': '/test_webservice'},
      WEBSERVICES_PUBLISH_ENDPOINT='resources',
      SQLALCHEMY_BINDS=None,
      SQLALCHEMY_DATABASE_URI='sqlite://',
      WTF_CSRF_ENABLED = False,
      TESTING = False,
      SITE_SECURE_URL='http://localhost',
      SECURITY_POST_LOGIN_VIEW='/postlogin',
      SECURITY_REGISTER_BLUEPRINT=True,
    )
    return app

  def test_app_config(self):
    self.assertIsNotNone(self.app.config['CACHE'])
    self.assertEqual(self.app.config['TEST_SPECIFIC_CONFIG'],'foo')

  def test_status_route(self):
    r = self.open('GET','/status')
    self.assertStatus(r,200)
  
  def test_protected_route(self):
    r = self.open('GET','/protected')
    self.assertStatus(r,200)
  
  def test_resources_route(self):
    r = self.open('GET','/test_webservice/resources')
    self.assertStatus(r,200)
    #Note:
    #https://github.com/adsabs/adsabs-webservices-blueprint/issues/9
    self.assertIn('/test_webservice/resources',r.json)
  
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
    r = self.open('POST','/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['POST'])

    r = self.open('GET','/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['GET'])

  def test_SCOPED(self):
    r = self.open('GET','/test_webservice/SCOPED')
    self.assertStatus(r,401)

  def test_LOW_RATE_LIMIT(self):
    go = lambda: self.open('GET','/test_webservice/LOW_RATE_LIMIT')
    r = go()
    self.assertStatus(r,200)
    r = go()
    self.assertStatus(r,200)
    r = go()
    self.assertStatus(r,429)    
    time.sleep(2)
    r = go()
    self.assertStatus(r,200)    

class DiscoverRemoteServerTestCase(ApiTestCase,DiscovererTestCase):
  '''
  . Run a third party service (actual webserver), including a /resources endpoint
  . create discoverer app, connecting to the service
  . Test that the app has the bootstrapped routes
  . Test GET, POST to the bootstrapped routes -> Backend services response
  . Requires that the remote service be a liveserver with >1 worker (https://github.com/adsabs/adsws/issues/19)
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
      SECURITY_REGISTER_BLUEPRINT=True,
      )
    self.tearDownRemoteServer()
    return app

  def setUp(self):
    self.setupRemoteServer()
    super(DiscoverRemoteServerTestCase,self).setUp()

  def tearDown(self):
    self.tearDownRemoteServer()
    super(DiscoverRemoteServerTestCase,self).tearDown()

  def test_app_config(self):
    self.assertIsNotNone(self.app.config['CACHE'])
    self.assertNotIn('TEST_SPECIFIC_CONFIG',self.app.config)

  def test_status_route(self):
    r = self.open('GET','/status')
    self.assertStatus(r,200)

  def test_protected_route(self):
    r = self.open('GET','/protected')
    self.assertStatus(r,200)

  def test_resources_route(self):
    r = self.open('GET','/test_webservice/resources')
    self.assertStatus(r,200)
    self.assertIn('/resources',r.json)

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
    r = self.open('POST','/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['POST'])

    r = self.open('GET','/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['GET'])

  def test_SCOPED(self):
    r = self.open('GET','/test_webservice/SCOPED')
    self.assertStatus(r,401)

  def test_LOW_RATE_LIMIT(self):
    #Note that this test may fail sometimes (but not often)
    #This happens when there is non-insignificant latency
    #between the remote server and this api
    #This shouldn't be a problem in production, as we don't really care
    #If an abuser manages to squeeze in 1-2 extra requests before ratelimit
    #really kicks in.
    go = lambda: self.open('GET','/test_webservice/LOW_RATE_LIMIT')
    r = go()
    self.assertStatus(r,200)
    self.assertIn('X-RateLimit-Remaining',r.headers)
    r = go()
    self.assertStatus(r,200)
    r = go()
    self.assertStatus(r,429)    
    time.sleep(2)
    r = go()
    self.assertStatus(r,200)

TESTSUITE = make_test_suite(DiscoverRemoteServerTestCase,DiscoverLocalModuleTestCase)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
