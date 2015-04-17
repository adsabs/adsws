from datetime import datetime

from adsws.testsuite import make_test_suite, run_test_suite
from adsws.core import db, user_manipulator
from flask.ext.testing import TestCase
from adsws.factory import create_app


class TestUsersModel(TestCase):
    """
    Test basic database operations on the Users model
    """

    def setUp(self):
        db.create_all(app=self.app)

    def tearDown(self):
        db.drop_all(app=self.app)

    def create_app(self):
        app = create_app(
            SQLALCHEMY_DATABASE_URI="sqlite://",
            EXTENSIONS=['adsws.ext.sqlalchemy'],
        )
        return app

    def test_users_crud_operations(self):
        """
        perform and test create, read, update, and delete patterns on user
        models using the `user_manipulator` service
        """

        # .new() should not save the User to the database
        joe = user_manipulator.new(email='joe')
        self.assertIsNone(user_manipulator.first(email='joe'))

        # .save() should save the User to the database
        user_manipulator.save(joe)
        u = user_manipulator.first(email='joe')
        self.assertIsNotNone(u)
        self.assertEqual(u.email, 'joe')

        # .create() should create immediately
        elias = user_manipulator.create(email='elias')
        u = user_manipulator.first(email='elias')
        self.assertIsNotNone(u)
        self.assertEqual(elias, u)

        # .update() should update immediately
        user_manipulator.update(elias, confirmed_at=datetime(2000, 1, 1))
        u = user_manipulator.first(email='elias')
        self.assertEqual(u.confirmed_at, datetime(2000, 1, 1))
        self.assertEqual(elias, u)

        # .delete() should delete immediately
        user_manipulator.delete(elias)
        u = user_manipulator.first(email='elias')
        self.assertIsNone(u)

        # even though this object was deleted in the db, we still should
        # have a reference to the python object
        self.assertIsNotNone(elias)
        self.assertEqual(elias.confirmed_at, datetime(2000, 1, 1))
    
        
TEST_SUITE = make_test_suite(TestUsersModel)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)