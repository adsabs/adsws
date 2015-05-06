import time
import datetime
from werkzeug.security import gen_salt

from flask.ext.testing import TestCase

from adsws.modules.oauth2server.models import OAuthClient, OAuthToken
from adsws.core.users import User
from adsws.core import db, user_manipulator
from adsws import factory
from adsws.testsuite import make_test_suite, run_test_suite
from adsws.accounts.manage import cleanup_tokens, cleanup_clients, \
    cleanup_users, parse_timedelta


class TestManage_Accounts(TestCase):
    """
    Tests for manage.py/flask.ext.script commands
    """

    def tearDown(self):
        db.drop_all(app=self.app)

    def setUp(self):
        """
        Sets up all of the users, clients, and tokens that management commands
        will run against.
        """

        db.create_all(app=self.app)

        now = datetime.datetime.now()
        delta = datetime.timedelta
        times = [
            now,
            now-delta(seconds=3),
            now+delta(seconds=3),
            now+delta(hours=1),
        ]
        self.times = times  # Save for comparisons in the tests

        # This is a user that has registered but not confirmed their account
        u = user_manipulator.create(
            email="unconfirmed@unittest",
            registered_at=now+delta(seconds=1),
        )
        db.session.add(u)

        # This is a user that has registered but not confirmed their account,
        # and furthermore will not have a registered_at attribute set
        u = user_manipulator.create(
            email="blankuser@unittest",
        )
        db.session.add(u)

        # This is a user that has registered and confirmed their account
        u = user_manipulator.create(
            email="user@unittest",
            registered_at=now,
            confirmed_at=now,
        )
        db.session.add(u)

        for _time in times:

            client = OAuthClient(
                user_id=u.id,
                client_id=gen_salt(20),
                client_secret=gen_salt(20),
                is_confidential=False,
                is_internal=True,
                _default_scopes="",
                last_activity=_time,
            )
            db.session.add(client)

            token = OAuthToken(
                client_id=client.client_id,
                user_id=u.id,
                access_token=gen_salt(20),
                refresh_token=gen_salt(20),
                expires=_time,
                _scopes="",
                is_personal=False,
                is_internal=True,
            )
            db.session.add(token)

        # Add a client without a last_activity to verify that the cleanup
        # scripts do not break under this condition
        client = OAuthClient(
            user_id=u.id,
            client_id=gen_salt(20),
            client_secret=gen_salt(20),
            is_confidential=False,
            is_internal=True,
            _default_scopes="",
        )
        db.session.add(client)

        # Add a token without an expiry to verify that the cleanup scripts
        # do not break under this condition
        token = OAuthToken(
            client_id=client.client_id,
            user_id=u.id,
            access_token=gen_salt(20),
            refresh_token=gen_salt(20),
            _scopes="",
            is_personal=False,
            is_internal=True,
        )
        db.session.add(token)
        db.session.commit()

    def create_app(self):
        app = factory.create_app(
            SQLALCHEMY_BINDS=None,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            EXTENSIONS=['adsws.ext.sqlalchemy'],
            DEBUG=False,
        )
        return app

    def test_parse_datetime(self):
        """
        Tests that a string formatted datetime is correctly parsed
        """
        td = parse_timedelta("days=31")
        self.assertIsInstance(td, datetime.timedelta)
        self.assertEqual(td.total_seconds(), 31*24*60*60)

        td = parse_timedelta("hours=23")
        self.assertIsInstance(td, datetime.timedelta)
        self.assertEqual(td.total_seconds(), 23*60*60)

    def test_cleanup_user(self):
        """
        Tests that unconfirmed users are properly expunged from the database
        as a result of the management:cleanup_users function
        """
        original_users = [u.email for u in db.session.query(User).all()]

        # This should not remove any users, since our one unconfirmed user
        # has a registration time of 1 second into the future
        # Additionally, ensure that users with a null registered_at attribute
        # should are not deleted
        cleanup_users(app_override=self.app, timedelta="seconds=0.1")
        users = [u.email for u in db.session.query(User).all()]
        self.assertItemsEqual(original_users, users)

        # After sleeping 1 second, registered_at should be now. Sleep for an
        # additional 0.1 sec so that cleanup_clients with timedelta=0.1s
        # should delete the "unconfirmed@unittest" user
        time.sleep(1.1)
        cleanup_users(app_override=self.app, timedelta="seconds=0.1")
        users = [u.email for u in db.session.query(User).all()]
        self.assertNotEqual(original_users, users)
        self.assertNotIn("unconfirmed@unittest", users)

    def test_cleanup_token(self):
        """
        Tests that expired oauth2tokens are properly removed from the database
        as a result of the cleanup_token procedure
        """
        original_tokens = db.session.query(OAuthToken).all()
        self.assertEqual(5, len(original_tokens))
        self.assertItemsEqual(
            filter(None, [i.expires for i in original_tokens]),
            self.times,
        )

        # Only those tokens which have already expired should be removed
        cleanup_tokens(app_override=self.app)
        current_tokens = db.session.query(OAuthToken).all()
        self.assertNotEqual(original_tokens, current_tokens)
        self.assertEqual(3, len(current_tokens))
        self.assertEqual(
            filter(None, [i.expires for i in current_tokens]),
            [i for i in self.times if i >= datetime.datetime.now()],
        )

        # Sleep to let one token expire
        # and check that this token has been removed after calling
        # the cleanup_tokens script again
        time.sleep(3)
        cleanup_tokens(app_override=self.app)
        current_tokens = db.session.query(OAuthToken).all()
        self.assertNotEqual(original_tokens, current_tokens)
        self.assertEqual(2, len(current_tokens))
        self.assertEqual(
            filter(None, [i.expires for i in current_tokens]),
            [i for i in self.times if i >= datetime.datetime.now()],
        )

    def test_cleanup_client(self):
        """
        Tests that oauth2clients whose last_activity attribute are properly
        removed from the database as a result of the cleanup_client procedure
        """
        original_clients = db.session.query(OAuthClient).all()
        self.assertEqual(5, len(original_clients))
        self.assertItemsEqual(
            filter(None, [i.last_activity for i in original_clients]),
            self.times,
        )

        # No clients should be cleaned
        cleanup_clients(app_override=self.app, timedelta="days=31")
        current_clients = db.session.query(OAuthClient).all()
        self.assertEqual(5, len(current_clients))

        # Cleanup all clients that are older than 0 seconds from now()
        cleanup_clients(app_override=self.app, timedelta="seconds=0")
        current_clients = db.session.query(OAuthClient).all()
        self.assertEqual(3, len(current_clients))

        # Wait 3 seconds, then perform the same cleanup. Should have one less
        # client after this operation.

        time.sleep(3.1)
        cleanup_clients(app_override=self.app, timedelta="seconds=0.1")
        current_clients = db.session.query(OAuthClient).all()
        self.assertEqual(2, len(current_clients))

        # Cleanup the client whose last_activity was set to 1 hour
        # into the future. This case should never happen in practice!
        cleanup_clients(app_override=self.app, timedelta="hours=-1")
        current_clients = db.session.query(OAuthClient).all()
        self.assertEqual(1, len(current_clients))

        # Only the client with last_activity=None should remain
        current_clients = db.session.query(OAuthClient).all()
        self.assertEqual(1, len(current_clients))
        self.assertIsNone(current_clients[0].last_activity)


TEST_SUITE = make_test_suite(TestManage_Accounts)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)