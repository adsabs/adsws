
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

    def create_app(self):
        app = api.create_app(
                SQLALCHEMY_DATABASE_URI='sqlite://',
                SITE_SECURE_URL='http://localhost',
                
                )
        
        blueprint = Blueprint('test', __name__)
        @api.route(blueprint, '/test')
        def test():
            return dict(foo='bar')
        
        @app.errorhandler(404)
        def handle_404(e):
            raise e

        db.create_all(app=app)
        app.register_blueprint(blueprint)
        
        return app
    
    def parse_redirect(self, location, parse_fragment=False):
        from werkzeug.urls import url_parse, url_decode, url_unparse
        scheme, netloc, script_root, qs, anchor = url_parse(location)
        return (
            url_unparse((scheme, netloc, script_root, '', '')),
            url_decode(anchor if parse_fragment else qs)
        )
        
        
    def test_headers(self):
        current_app.config['CORS_DOMAINS'] = {'http://localhost': 1}
        
        r = self.client.get('/test', headers=[('Origin', 'http://localhost')])
        self.assertEqual(r.headers.get('Access-Control-Allow-Origin'), 'http://localhost')
        
        r = self.client.get('/test', headers=[('Origin', 'http://localhost:5000')])
        self.assertEqual(r.headers.get('Access-Control-Allow-Origin', None), None)
        
        
        
TESTSUITE = make_test_suite(ApiTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
