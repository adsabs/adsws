from flask import Flask, session, url_for, request, jsonify, Blueprint, current_app
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
from adsws import discoverer
import requests
import httpretty
import json

class Stubdata:
  resources_route = {
      "/resc1": {
        "description": "desc for resc1",
        "methods": [
          "GET"
        ],
        "scopes": []
      },
      "/resc2": {
        "description": "desc for resc2",
        "methods": [
          "POST"
        ],
        "scopes": []
      },
      "/resc3": {
        "description": "desc for resc3",
        "methods": [
          "GET",
          "POST",
        ],
        "scopes": []
      },
      "/resources": {
        "description": "Overview of available resources",
        "methods": [
          "GET"
        ],
        "scopes": []
      }
    }

  resc1 = {'resource': 'resc1'}
  resc2 = {'resource': 'resc2'}
  resc3_get =  {'resource': 'resc3','method':'get'}
  resc3_post = {'resource': 'resc3','method':'post'}


class DiscovererTestCase(FlaskAppTestCase):
  '''
  . Mock third party services, including a /resources endpoint
  . create discoverer app, connecting to the mocked resources
  . Test that current_app has the bootstrapped routes
  . Test GET, POST to the bootstrapped routes -> Backend services response

  '''
  def create_app(self):
    '''
    This method creates the mocked third-party webservices in addition to the discoverer
    '''

    #Webservice on localhost:1233 which provides:
    # /resources
    # /resc1, methods GET
    # /resc2, methods POST
    # /resc3, methods GET,POST
    httpretty.enable()
    httpretty.register_uri(httpretty.GET, "http://localhost:1233/resources",
                           body=json.dumps(Stubdata.resources_route),
                           content_type="application/json")

    httpretty.register_uri(httpretty.GET, "http://localhost:1233/resc1",
                           body=json.dumps(Stubdata.resc1),
                           content_type="application/json")

    httpretty.register_uri(httpretty.POST, "http://localhost:1233/resc2",
                           body=json.dumps(Stubdata.resc2),
                           content_type="application/json")

    httpretty.register_uri(httpretty.GET, "http://localhost:1233/resc3",
                           body=json.dumps(Stubdata.resc3_get),
                           content_type="application/json")
    httpretty.register_uri(httpretty.POST, "http://localhost:1233/resc3",
                           body=json.dumps(Stubdata.resc3_post),
                           content_type="application/json")

    app_config = {
      'WEBSERVICES': {
        # uri : deploy_path
        'http://localhost:1233/': '/test_webservice',
      },
      'WEBSERVICES_PUBLISH_ENDPOINT':'resources',
    }
    app = discoverer.create_app(**app_config)
    return app

  def test_resources_route(self):
    r = self.client.get('/test_webservice/resources')
    self.assertEqual(r.json,Stubdata.resources_route)
        
  def test_resc1(self):
    r = self.client.get('/test_webservice/resc1')
    self.assertEqual(r.json,Stubdata.resc1)

    r = self.client.post('/test_webservice/resc1')
    self.assertEqual(r.status_code,405) #Expect to get 405 METHOD NOT ALLOWED

  def test_resc2(self):
    r = self.client.post('/test_webservice/resc2')
    self.assertEqual(r.json,Stubdata.resc2)

    r = self.client.get('/test_webservice/resc2')
    self.assertEqual(r.status_code,405) #Expect to get 405 METHOD NOT ALLOWED

  def test_resc3(self):
    r = requests.get("http://localhost:1233/resc3")
    self.assertEqual(r.json(),Stubdata.resc3_get)

    r = requests.post("http://localhost:1233/resc3")
    self.assertEqual(r.json(),Stubdata.resc3_post)

    r = self.client.post('/test_webservice/resc3')
    self.assertEqual(r.json,Stubdata.resc3_post)

    r = self.client.get('/test_webservice/resc3')
    self.assertEqual(r.json,Stubdata.resc3_get)

TESTSUITE = make_test_suite(DiscovererTestCase)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
