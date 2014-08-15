from adsws.testsuite import make_test_suite, \
    run_test_suite, AdsWSAppTestCase, FlaskAppTestCase, AdsWSTestCase

from adsws.factory import create_app
from adsws.core import db
from flask import Flask

class UsersTest(FlaskAppTestCase):
    
    def create_app(self):
        app = Flask(__name__)
        db.init_app(app)
        db.create_all(app=app)
        return app
    
    def test_sqlalchemy(self):
        from adsws.core import client_manipulator
        user = client_manipulator.new(login='joe@email.com')
        
        userx = client_manipulator.first(login='joe@email.com')
        self.assertEqual(userx, None, 'user was there, and shouldnt')

        client_manipulator.save(user)
        
        user = client_manipulator.first(login='joe@email.com')
        self.assertEqual(user.login, 'joe@email.com', 'user not saved')
        
        from adsws.core.clients.models import Client
        user = Client(login='elias@email.com')
        db.session.add(user)
        db.session.commit()
        
        user = client_manipulator.first(login='elias@email.com')
        self.assertEqual(user.login, 'elias@email.com', 'user not saved')
    
        
TEST_SUITE = make_test_suite(UsersTest)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)        
    