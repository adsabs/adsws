
import os


from adsws.testsuite import unittest, make_test_suite, run_test_suite

from threading import Thread
import requests

from splinter import Browser

def run_server(server):
    server.serve_forever()

class DeploymentTestCase(unittest.TestCase):
    '''Verify the basic mechanisms.'''

    def setUp(self):
        import wsgi
        from werkzeug.serving import make_server
        app = wsgi.application
        self.host = '0.0.0.0'
        self.port = 19956
        self.server = make_server(self.host, self.port, app=app, threaded=False, processes=1,
                request_handler=None, passthrough_errors=False,
                ssl_context=None)
        Thread(target=run_server, args=(self.server, )).start()
        self.browser = Browser()
        
    def tearDown(self):
        self.server.shutdown()
        self.browser.quit()
    
    def get(self, url):
        return requests.get(self.url(url))
    
    def url(self, path):
        return 'http://%s:%s%s' % (self.host, self.port, path)
        
    def test_login(self):
        
        r = self.get('/login')
        self.assertRegexpMatches(r.text, r'<input id\=\"csrf_token\"', "missing login")
        
        b = self.browser
        b.visit(self.url('/login'))
        b.fill('email', 'test@test.org')
        b.fill('password', 'test')
        b.find_by_name('submit').first.click()

        
        
        
    
        
TESTSUITE = make_test_suite(DeploymentTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
