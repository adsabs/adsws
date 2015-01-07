
import os

from flask import Flask, session, url_for, request, jsonify, Blueprint, current_app

from adsws.core import db
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
from adsws import api

from mock import MagicMock
try:
    from six.moves.urllib.parse import urlparse
except ImportError:
    from urllib.parse import urlparse



class ApiTestCase(FlaskAppTestCase):
    '''Verify the basic mechanisms.'''

    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_BINDS = None
    CORS_DOMAINS = ['http://localhost','localhost:5000','localhost']
    CORS_METHODS = ['GET', 'OPTIONS', 'POST', 'PUT']
    CORS_HEADERS = ['content-type','X-BB-Api-Client-Version','Authorization','Accept','foo']
    WEBSERVICES = {}

    def create_app(self):
        app = api.create_app(
                SQLALCHEMY_DATABASE_URI=self.SQLALCHEMY_DATABASE_URI,
                SQLALCHEMY_BINDS=self.SQLALCHEMY_BINDS,
                CORS_DOMAINS = self.CORS_DOMAINS,
                CORS_HEADERS = self.CORS_HEADERS,
                CORS_METHODS = self.CORS_METHODS,
                WEBSERVICES = self.WEBSERVICES,
                )
        db.create_all(app=app)
        return app
    
    # def parse_redirect(self, location, parse_fragment=False):
    #     from werkzeug.urls import url_parse, url_decode, url_unparse
    #     scheme, netloc, script_root, qs, anchor = url_parse(location)
    #     return (
    #         url_unparse((scheme, netloc, script_root, '', '')),
    #         url_decode(anchor if parse_fragment else qs)
    #     )
        
    def test_allow_origin(self):
        r = self.client.get('/status', headers=None)
        self.assertStatus(r,200)

        for origin in ['http://localhost','localhost:5000','localhost']:
            r = self.client.get('/status', headers={'Origin':origin})
            self.assertStatus(r,200)
            self.assertTrue(origin in r.headers.get('Access-Control-Allow-Origin'))

    def compareHeaders(self,header_,list_):
        if isinstance(header_,basestring):
            header_ = [i.strip() for i in header_.split(',')]
        self.assertEqual(sorted(header_),sorted(list_))

    def test_options(self):
        r = self.client.options('/status', headers={
                        'Origin': 'http://localhost',
                        'Access-Control-Request-Method': 'OPTIONS',
                        'Access-Control-Request-Headers': 'accept, x-bb-api-client-version, content-type'
                        })
        self.assertIn('Access-Control-Allow-Methods', r.headers)
        self.assertIn('Access-Control-Allow-Headers', r.headers)

        self.compareHeaders(r.headers['Access-Control-Allow-Methods'],self.CORS_METHODS)
        self.compareHeaders(r.headers['Access-Control-Allow-Headers'],self.CORS_HEADERS)
        
        
TESTSUITE = make_test_suite(ApiTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
