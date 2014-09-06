
import os
import logging
import json
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
from flask import Flask, session, url_for, request, jsonify, abort
from adsws import api
from adsws.core import user_manipulator, db
from flask_login import current_user, login_user, logout_user
from datetime import datetime, timedelta

from flask_oauthlib.client import OAuth
from mock import MagicMock
from flask_oauthlib.client import prepare_request
try:
    from six.moves.urllib.parse import urlparse
except ImportError:
    from urllib.parse import urlparse


logging.basicConfig(level=logging.DEBUG)

class ApiTestCase(FlaskAppTestCase):
    '''Authenticate users using ADS Classic (if necessary)'''

    def create_app(self):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'True'
        
        app = api.create_app(
                SQLALCHEMY_DATABASE_URI='sqlite://',
                WTF_CSRF_ENABLED = False,
                TESTING = True,
                SITE_SECURE_URL='http://localhost',
                SECURITY_POST_LOGIN_VIEW='/postlogin'
                )
        
        @app.route('/postlogin')
        def username():
            if current_user.is_authenticated():
                return current_user.email
            return u'Anonymous'
        
        @app.errorhandler(404)
        def handle_404(e):
            raise e

        db.create_all(app=app)
        return app
    
    def parse_redirect(self, location, parse_fragment=False):
        from werkzeug.urls import url_parse, url_decode, url_unparse
        scheme, netloc, script_root, qs, anchor = url_parse(location)
        return (
            url_unparse((scheme, netloc, script_root, '', '')),
            url_decode(anchor if parse_fragment else qs)
        )
        
    def setUp(self):
        FlaskAppTestCase.setUp(self)
        
        user = user_manipulator.create(email='montysolr', password='montysolr', active=True)
        user_manipulator.create(email='villain', password='villain', active=True)
        
        from adsws.modules.oauth2server.models import OAuthClient, Scope, OAuthToken
        from adsws.modules.oauth2server.registry import scopes as scopes_registry
        
        # Register a test scope
        scopes_registry.register(Scope('api:search'))
        self.base_url = self.app.config.get('SITE_SECURE_URL')
        
        # create a client in the database
        c1 = OAuthClient(
            client_id='bumblebee',
            client_secret='client secret',
            name='bumblebee',
            description='',
            is_confidential=False,
            user_id=user.id,
            _redirect_uris='%s/client/authorized' % self.base_url,
            _default_scopes="test:scope"
        )
        db.session.add(c1)
        db.session.commit()
        
        self.oauth = OAuth(self.app)
        
        
    def authenticate(self):
        
        self.remote_client = create_client(self.app,
                               'bumblebee',
                               consumer_key='bumblebee', 
                               consumer_secret='client secret',
                               request_token_params={'scope': 'api:search'})
        
        # authorize the user - normally, this would happen as a middle step
        # before /oauth/authorize is accessed
        print 'test', id(session._get_current_object())
        self.login('montysolr', 'montysolr')
        
        # 0. client authentication
        
        # this doesn't work because the session object will be different
        # r = self.remote_client.authorize(callback=url_for('authorized', _external=True))
        print 'test', id(session._get_current_object())
        r = self.client.get('/oauth2test/login')
        next_url, data = self.parse_redirect(r.location)
        
        # 2. user grants permissions to the client
        data['confirm'] = 'yes'
        data['scope'] = 'api:search'
        
        r = self.client.post(url_for('oauth2server.authorize'), 
                             data=data)
        next_url, data = self.parse_redirect(r.location)
        self.assertEqual(next_url, url_for('authorized', _external=True))
        
        # 3. oauth2 server redirects to /client/authorized
        # 4. client at /client/authorized saves the 'access_token'
        r = self.client.get(next_url, query_string=data)
        resp = json.loads(r.data)
        self.assertTrue('access_token' in resp)
        
        print 'test', id(session._get_current_object())
        self.assertEqual(self.remote_client.get_request_token(), resp['access_token'])
        print self.remote_client.get_request_token()
        
        

        if False:
            print r.data
        
            r = self.remote_client.authorize(callback=url_for('authorized', _external=True))
            print r.location
            
            r = self.client.get(r.location.split('?')[0], query_string=r.location.split('?')[1])
            
            expires = datetime.utcnow() + timedelta(seconds=3600)
            tok = OAuthToken(
                access_token='secret token',
                refresh_token='secret token',
                _scopes='api:search api:update',
                expires=expires,
                client=c1,
                user=user,
                is_personal=False,
            )
            db.session.add(tok)
            db.session.commit()

        

    def test_search(self):
        print 'test', id(session._get_current_object())
        self.authenticate()
        resp = self.remote_client.get('/api/1/search')
        print resp.data



def create_client(app, name, **kwargs):
    """Helper function to create a OAuth2 client to test an OAuth2 provider."""
    default = dict(
        consumer_key='confidential',
        consumer_secret='confidential',
        request_token_params={'scope': 'test:scope'},
        base_url=app.config['SITE_SECURE_URL'],
        request_token_url=None,
        access_token_method='POST',
        access_token_url='%s/oauth/token' % app.config['SITE_SECURE_URL'],
        authorize_url='%s/oauth/authorize' % app.config['SITE_SECURE_URL'],
    )
    default.update(kwargs)

    oauth = OAuth(app)
    remote = oauth.remote_app(name, **default)
    print 'client', id(session._get_current_object())
    
    @app.route('/oauth2test/login')
    def login():
        return remote.authorize(callback=url_for('authorized', _external=True))

    @app.route('/oauth2test/logout')
    def logout():
        session.pop('confidential_token', None)
        return "logout"
    
    @app.route('/client/authorized')
    @remote.authorized_handler
    def authorized(resp):
        if resp is None:
            return 'Access denied: error=%s' % (
                request.args.get('error', "unknown")
            )
        if isinstance(resp, dict) and 'access_token' in resp:
            session['confidential_token'] = (resp['access_token'], '')
            print id(session._get_current_object())
            print 'client', id(session._get_current_object())
            return jsonify(resp)
        return str(resp)

    @remote.tokengetter
    def get_oauth_token():
        print 'client', id(session._get_current_object())
        return session.get('confidential_token')
    
    def patch_request(app):
        test_client = app.test_client()

        def make_request(uri, headers=None, data=None, method=None):
            uri, headers, data, method = prepare_request(
                uri, headers, data, method
            )
            if not headers and data is not None:
                headers = {
                    'Content-Type': ' application/x-www-form-urlencoded'
                }

            # test client is a `werkzeug.test.Client`
            parsed = urlparse(uri)
            uri = '%s?%s' % (parsed.path, parsed.query)
            resp = test_client.open(
                uri, headers=headers, data=data, method=method
            )
            # for compatible
            resp.code = resp.status_code
            return resp, resp.data
        return make_request
    
    remote.http_request = MagicMock(
                side_effect=patch_request(app)
            )
    
    return remote


TESTSUITE = make_test_suite(ApiTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
