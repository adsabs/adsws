from flask import Flask, session, url_for, request, jsonify, Blueprint, current_app
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
from api_base import ApiTestCase, create_client
from adsws import discoverer
import requests
import httpretty
import json

class Stubdata:
  resources_route = {
      "/GET": {
        "description": "desc for resc1",
        "methods": [
          "GET"
        ],
        "scopes": [],
        "rate_limit": [1000,60*60*24],
      },
      "/POST": {
        "description": "desc for resc2",
        "methods": [
          "POST"
        ],
        "scopes": [],
        "rate_limit": [1000,60*60*24],

      },
      "/GETPOST": {
        "description": "desc for resc3",
        "methods": [
          "GET",
          "POST",
        ],
        "scopes": [],
        "rate_limit": [1000,60*60*24],

      },
      "/SCOPED": {
        "description": "desc for resc3",
        "methods": [
          "GET",
        ],
        "scopes": ['this-scope-shouldnt-exist'],
        "rate_limit": [1000,60*60*24],

      },
      "/resources": {
        "description": "Overview of available resources",
        "methods": [
          "GET"
        ],
        "scopes": [],
        "rate_limit": [1000,60*60*24],
      }
    }

  GET = {'resource': 'GET'}
  POST = {'resource': 'POST'}
  GETPOST = {
    'GET': {'resource': 'GETPOST','method':'get'},
    'POST': {'resource': 'GETPOST','method':'post'},
  }


class DiscovererTestCase(ApiTestCase):
  '''
  . Mock third party services, including a /resources endpoint
  . create discoverer app, connecting to the mocked resources
  . Test that current_app has the bootstrapped routes
  . Test GET, POST to the bootstrapped routes -> Backend services response

  '''
  httpretty.enable()
  httpretty.register_uri(httpretty.GET, "http://localhost:1233/resources",
                         body=json.dumps(Stubdata.resources_route),
                         content_type="application/json")

  httpretty.register_uri(httpretty.GET, "http://localhost:1233/GET",
                         body=json.dumps(Stubdata.GET),
                         content_type="application/json")

  httpretty.register_uri(httpretty.POST, "http://localhost:1233/POST",
                         body=json.dumps(Stubdata.POST),
                         content_type="application/json")

  httpretty.register_uri(httpretty.GET, "http://localhost:1233/GETPOST",
                         body=json.dumps(Stubdata.GETPOST['GET']),
                         content_type="application/json")
  httpretty.register_uri(httpretty.POST, "http://localhost:1233/GETPOST",
                         body=json.dumps(Stubdata.GETPOST['POST']),
                         content_type="application/json")

  discoverer_app = discoverer.create_app(
    WEBSERVICES = {'http://localhost:1233/': '/test_webservice'},
    WEBSERVICES_PUBLISH_ENDPOINT='resources',
    SQLALCHEMY_BINDS=None,
    SQLALCHEMY_DATABASE_URI='sqlite://',
    )
  discoverer_test_client = discoverer_app.test_client()
  def open(self,method,url):
    return self.discoverer_test_client.open(url,method=method,headers={"Authorization": "Bearer %s" % self.token})

  def test_status_route(self):
    r = self.open('GET','/status')
    self.assertStatus(r,200)

  def test_resources_route(self):
    print "test_resources_route, about to self.open"
    r = self.open('GET','/test_webservice/resources') 
    print r
    print r.data
    self.assertEqual(r.json,Stubdata.resources_route)

  # def test_GET_resc(self):
  #   r = self.client.get('/test_webservice/GET')
  #   self.assertEqual(r.json,Stubdata.GET)

  #   r = self.client.post('/test_webservice/GET')
  #   self.assertEqual(r.status_code,405) #Expect to get 405 METHOD NOT ALLOWED

  # def test_POST_resc(self):
  #   r = self.client.post('/test_webservice/POST')
  #   self.assertEqual(r.json,Stubdata.POST)

  #   r = self.client.get('/test_webservice/POST')
  #   self.assertEqual(r.status_code,405) #Expect to get 405 METHOD NOT ALLOWED

  # def test_GETPOST_resc(self):
  #   r = requests.get("http://localhost:1233/GETPOST")
  #   self.assertEqual(r.json(),Stubdata.GETPOST['GET'])

  #   r = requests.post("http://localhost:1233/GETPOST")
  #   self.assertEqual(r.json(),Stubdata.GETPOST['POST'])

  #   r = self.client.post('/test_webservice/GETPOST')
  #   self.assertEqual(r.json,Stubdata.GETPOST['POST'])

  #   r = self.client.get('/test_webservice/GETPOST')
  #   self.assertEqual(r.json,Stubdata.GETPOST['GET'])

  # def test_SCOPED(self):
  #   r = self.client.get('/test_webservice/SCOPED')
  #   self.assertEqual(r.status_code,401)
  #   #TODO: Make the scope, pass the token, see if we get 200 OK

TESTSUITE = make_test_suite(DiscovererTestCase)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
