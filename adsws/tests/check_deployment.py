
import os
import socket
import tempfile
import subprocess

from adsws.testsuite import unittest, make_test_suite, run_test_suite
from adsws import factory

from threading import Thread
import requests

from splinter import Browser
from adsws.core import db

def run_server(server):
    server.serve_forever()

DEBUG = False

class DeploymentTestCase(unittest.TestCase):
    '''Verify the site installation.'''

    def setUp(self):

        self.oldwd = os.getcwd()
        os.chdir(factory.get_root_path() + '/..')

        # since we simulate the real application
        # we cannot use in-memory instance of database

        database_uri = 'sqlite:///%s/foo.sqlite' % tempfile.gettempdir().replace('\\', '/')
        self.tf = tempfile.mktemp()
        fd = open(self.tf, 'w')
        fd.write('''
SQLALCHEMY_DATABASE_URI = '%s'
SQLALCHEMY_ECHO = False
        ''' % (database_uri,)
        )
        fd.close()

        os.environ['ADSWS_SETTINGS'] = self.tf

        self.check_alembic_reads_correct_database(database_uri)

        # run the real alembic upgrade head
        # the app will read the correct db setting
        from pkg_resources import load_entry_point
        load_entry_point('alembic', 'console_scripts', 'alembic')(['upgrade', 'head'])


        import wsgi
        reload(wsgi)
        from werkzeug.serving import make_server
        app = wsgi.application

        self.apps = [app.app]
        for k,v in app.mounts.items():
            self.apps.append(v)

        # check (to be sure)
        for a in self.apps:
            with a.app_context() as c:
                assert a.config.get('SQLALCHEMY_DATABASE_URI') == database_uri

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

        #for a in self.apps:
        #    with a.app_context() as c:
        #        db.drop_all(app=a)
        self.apps = []

        #from pkg_resources import load_entry_point
        #load_entry_point('alembic', 'console_scripts', 'alembic')(['downgrade', 'base'])
        x = subprocess.check_output(['alembic', 'downgrade', 'base'])

        os.remove(self.tf)
        os.chdir(self.oldwd)

    def check_alembic_reads_correct_database(self, db_uri):
        x = subprocess.check_output(['alembic', 'current'])
        print x
        if not 'Current revision for ' + db_uri in x:
            raise Exception('Ooohooo, refusing to run this test, it would change your db! Do you have use_flask_db_url in your alembic.ini?')


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

        self.assertTrue(b.is_text_present('Specified user does not exist'))
        
        # it doesnt log you when accessing again
        b.visit(self.url('/login'))
        self.assertTrue(b.is_text_present('Remember Me'))
        
        b.visit(self.url('/'))
        self.assertTrue(b.is_text_present('Hello Anonymous.'))
        
    def test_api_bootstrap(self):
        import json
        r = self.get('/v1/bumblebee/bootstrap')
        self.assertRegexpMatches(r.text, r'access_token')
        
        d = json.loads(r.text)
        
        r = requests.get(self.url('/v1/info'), headers={'Authorization': 'Bearer:' + d['access_token']})
        self.assertTrue(u"You are accessing API version 'v1' as user 'anonymous@adslabs.org'." in r.text)

    def test_register(self):
        b = self.getBrowser()
        b.visit(self.url('/register'))
        b.fill('email', 'test@test.org')
        b.fill('password', 'testtt')
        b.fill('password_confirm', 'testtt')
        b.find_by_name('submit').first.click()
        self.assertTrue(b.is_text_present('Hello test@test.org.'))

        b.visit(self.url('/logout'))
        self.assertTrue(b.is_text_present('Hello Anonymous.'))
    
        b.visit(self.url('/login'))
        b.fill('email', 'test@test.org')
        b.fill('password', 'testtt')
        b.find_by_name('submit').first.click()


    def test_ads_classic_login_fallback(self):
        b = self.getBrowser()
        b.visit(self.url('/login'))
        b.fill('email', 'fooadslabs@hmamail.com')
        b.fill('password', 'heyjoe')
        b.find_by_name('submit').first.click()
        self.assertTrue(b.is_text_present('Hello fooadslabs@hmamail.com.'))

TESTSUITE = make_test_suite(DeploymentTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
