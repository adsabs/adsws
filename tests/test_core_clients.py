from adsws.testsuite import make_test_suite, \
    run_test_suite, FlaskAppTestCase

from adsws.core import db
from flask import Flask

class UsersTest(FlaskAppTestCase):
    
    def create_app(self):
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.init_app(app)
        db.create_all(app=app)
        return app
    
    def test_sqlalchemy(self):
        from adsws.core import user_manipulator
        user = user_manipulator.new(login='joe@email.com')
        
        userx = user_manipulator.first(login='joe@email.com')
        self.assertEqual(userx, None, 'user was there, and shouldnt')

        user_manipulator.save(user)
        
        user = user_manipulator.first(login='joe@email.com')
        self.assertEqual(user.login, 'joe@email.com', 'user not saved')
        
        from adsws.core.users.models import User
        user = User(login='elias@email.com')
        db.session.add(user)
        db.session.commit()
        
        user = user_manipulator.first(login='elias@email.com')
        self.assertEqual(user.login, 'elias@email.com', 'user not saved')
    
        
TEST_SUITE = make_test_suite(UsersTest)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)        
    