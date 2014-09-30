
import os
import socket
import tempfile

from adsws.testsuite import unittest, make_test_suite, run_test_suite

from threading import Thread
import requests

from splinter import Browser
from adsws.core import db

def run_server(server):
    server.serve_forever()

DEBUG = False

class DeploymentTestCase(unittest.TestCase):
    '''Verify the basic mechanisms.'''

    def setUp(self):
        
        self.tf = tempfile.mktemp()
        fd = open(self.tf, 'w')
        fd.write('''
SQLALCHEMY_DATABASE_URI = 'sqlite://'
        '''
        )
        fd.close()
              
        os.environ['ADSWS_SETTINGS'] = self.tf
        
        
        import wsgi
        from werkzeug.serving import make_server
        app = wsgi.application
        
        db.create_all(app=app.app)
        
        self.host = '127.0.0.1'
        
        if DEBUG:
            port = 19956
        else: 
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            
        
        self.port = port
        self.server = make_server(self.host, self.port, app=app, threaded=False, processes=1,
                request_handler=None, passthrough_errors=False,
                ssl_context=None)
        self.thread = Thread(target=run_server, args=(self.server, ))
        self.thread.start()
        self.browsers = []
        
    def tearDown(self):
        self.server.shutdown()
        self.thread.join(500)
        for b in self.browsers:
            b.quit()
        os.remove(self.tf)
    
    def getBrowser(self):
        b = Browser()
        self.browsers.append(b)
        return b
    
    def get(self, url):
        return requests.get(self.url(url))
    
    def url(self, path):
        return 'http://%s:%s%s' % (self.host, self.port, path)
        
    def test_login(self):
        """
        can login - access account - but going to api
        does nothing
        """
        r = self.get('/login')
        self.assertRegexpMatches(r.text, r'<input id\=\"csrf_token\"', "missing login")
        
        b = self.getBrowser()
        b.visit(self.url('/login'))
        b.fill('email', 'test@test.org')
        b.fill('password', 'test')
        b.find_by_name('submit').first.click()

        b.is_text_present('Specified user does not exist')
        
        # it doesnt log you when accessing again
        b.visit(self.url('/login'))
        b.is_text_present('Remember me')
        
        b.visit(self.url('/'))
        b.is_text_present('Hello Anonymous.')
        
    def test_api_bootstrap(self):
        import json
        r = self.get('/v1/bumblebee/bootstrap')
        self.assertRegexpMatches(r.text, r'access_token')
        
        d = json.loads(r.text)
        
        r = requests.get(self.url('/v1/info'), headers={'Authorization': 'Bearer:' + d['access_token']})
        self.assertTrue(u"You are accessing API version 'v1' as user 'anonymous@adslabs.org'." in r.text)
    
        
TESTSUITE = make_test_suite(DeploymentTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
