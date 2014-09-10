
from adsws.testsuite import FlaskAppTestCase, make_test_suite, run_test_suite
from flask import Flask, session, url_for
from adsws import frontend
from adsws.core import user_manipulator, db
from flask_login import current_user, login_user, logout_user

class LoginTestCase(FlaskAppTestCase):
    '''Authenticate users using ADS Classic (if necessary)'''

    def create_app(self):
        app = frontend.create_app(
                SQLALCHEMY_DATABASE_URI='sqlite://',
                WTF_CSRF_ENABLED = False,
                TESTING = True,
                SECURITY_POST_LOGIN_VIEW='/welcome'
                )

        @app.route('/welcome')
        def index():
            return u'Welcome!'

        
        @app.route('/username')
        def username():
            if current_user.is_authenticated():
                return current_user.email
            return u'Anonymous'

        
        @app.route('/empty_session')
        def empty_session():
            return unicode(u'modified=%s' % session.modified)

        # This will help us with the possibility of typoes in the tests. Now
        # we shouldn't have to check each response to help us set up state
        # (such as login pages) to make sure it worked: we will always
        # get an exception raised (rather than return a 404 response)
        @app.errorhandler(404)
        def handle_404(e):
            raise e

        db.create_all(app=app)
        return app
      
    def setUp(self):
        FlaskAppTestCase.setUp(self)
        
        user_manipulator.create(email='admin', password='admin', active=True)
        user_manipulator.create(email='villain', password='villain', active=True)
        user_manipulator.create(email='client', password='client', active=True)
        
            

    def _get_remember_cookie(self, test_client):
        our_cookies = test_client.cookie_jar._cookies['localhost.local']['/']
        return our_cookies[self.remember_cookie_name]

    def _delete_session(self, c):
        # Helper method to cause the session to be deleted
        # as if the browser was closed. This will remove
        # the session regardless of the permament flag
        # on the session!
        with c.session_transaction() as sess:
            sess.clear()

    #
    # Login
    #
    def test_test_request_context_users_are_anonymous(self):
        with self.app.test_request_context():
            self.assertTrue(current_user.is_anonymous())

    def test_defaults_anonymous(self):
        with self.app.test_client() as c:
            result = c.get('/username')
            self.assertEqual(u'Anonymous', result.data.decode('utf-8'))
            
        with self.app.test_client() as c:
            result = c.post(url_for('security.login'), 
                            data=dict(email='admin', password='admin'), 
                            follow_redirects=True)
            self.assertEqual(result.data, 'Welcome!')
            result = c.get(url_for('username'))
            self.assertEqual(result.data, 'admin')
            

    def test_login_user(self):
        u = self.login('admin', 'admin')
        self.assertTrue('/welcome' in u.location)
        
    def test_session_is_saved(self):
        from adsws.ext.session.backends.sqlalchemy import Session
        s = Session.query.first()
        self.assertEqual(s, None)
        self.client.get('/username')
        s = Session.query.first()
        self.assertEqual(s.uid, -1)
        
        with self.app.test_client() as c:
            c.get('/username')
            
        c = Session.query.count()
        self.assertEqual(c, 2)

TESTSUITE = make_test_suite(LoginTestCase)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)
