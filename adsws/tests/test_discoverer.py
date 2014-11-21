from flask import Flask, session, url_for, request, jsonify, Blueprint, current_app
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
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
        "scopes": []
      },
      "/POST": {
        "description": "desc for resc2",
        "methods": [
          "POST"
        ],
        "scopes": []
      },
      "/GETPOST": {
        "description": "desc for resc3",
        "methods": [
          "GET",
          "POST",
        ],
        "scopes": []
      },
      "/SCOPED": {
        "description": "desc for resc3",
        "methods": [
          "GET",
        ],
        "scopes": ['this-scope-shouldnt-exist']
      },
      "/ECHOPOST" : {
        "description": "should echo back the post body",
        "methods" : ['POST'],
        "scopes": [],
      },
      "/resources": {
        "description": "Overview of available resources",
        "methods": [
          "GET"
        ],
        "scopes": []
      }
    }

  GET = {'resource': 'GET'}
  POST = {'resource': 'POST'}
  GETPOST = {
    'GET': {'resource': 'GETPOST','method':'get'},
    'POST': {'resource': 'GETPOST','method':'post'},
  }


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


    def post_request_callback(request,uri,headers):
      return (200,headers,request.body)


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

    httpretty.register_uri(httpretty.POST, "http://localhost:1233/ECHOPOST",
                           body=post_request_callback,
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

  def test_ECHOPOST_resc(self):
    data = {'foo':'bar'}
    r = requests.post('http://localhost:1233/ECHOPOST',data=json.dumps(data))
    self.assertEqual(r.json(),data)
    r = self.client.post('/test_webservice/ECHOPOST',data=json.dumps(data))
    #self.assertEqual(r.json,data)

  def test_GET_resc(self):
    r = self.client.get('/test_webservice/GET')
    self.assertEqual(r.json,Stubdata.GET)

    r = self.client.post('/test_webservice/GET')
    self.assertEqual(r.status_code,405) #Expect to get 405 METHOD NOT ALLOWED

  def test_POST_resc(self):
    r = self.client.post('/test_webservice/POST')
    self.assertEqual(r.json,Stubdata.POST)

    r = self.client.get('/test_webservice/POST')
    self.assertEqual(r.status_code,405) #Expect to get 405 METHOD NOT ALLOWED

  def test_GETPOST_resc(self):
    r = requests.get("http://localhost:1233/GETPOST")
    self.assertEqual(r.json(),Stubdata.GETPOST['GET'])

    r = requests.post("http://localhost:1233/GETPOST")
    self.assertEqual(r.json(),Stubdata.GETPOST['POST'])

    r = self.client.post('/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['POST'])

    r = self.client.get('/test_webservice/GETPOST')
    self.assertEqual(r.json,Stubdata.GETPOST['GET'])

  def test_SCOPED(self):
    r = self.client.get('/test_webservice/SCOPED')
    self.assertEqual(r.status_code,401)
    #TODO: Make the scope, pass the token, see if we get 200 OK

TESTSUITE = make_test_suite(DiscovererTestCase)

if __name__ == '__main__':
  run_test_suite(TESTSUITE)
