import time
import datetime
from werkzeug.security import gen_salt

from flask.ext.testing import TestCase

from adsws.modules.oauth2server.models import OAuthClient, OAuthToken
from adsws.core import db, user_manipulator
from adsws import factory
from adsws.testsuite import make_test_suite, run_test_suite
from adsws.accounts.manage import cleanup_tokens


class TestManage_Accounts(TestCase):
    """
    Tests for manage.py/flask.ext.script commands
    """

    def tearDown(self):
        db.drop_all(app=self.app)

    def setUp(self):
        db.create_all(app=self.app)

        u = user_manipulator.create(
            email="user@unittest"
        )
        db.session.add(u)

        client = OAuthClient(
            user_id=u.id,
            name="user-client",
            client_id=gen_salt(20),
            client_secret=gen_salt(20),
            is_confidential=False,
            is_internal=True,
            _default_scopes="",
        )
        db.session.add(client)

        now = datetime.datetime.now()
        delta = datetime.timedelta
        expires = [
            now,  # already expired
            now-delta(seconds=3),  # already expired
            now+delta(seconds=3),   # expired only after time.sleep(5)
            now+delta(hours=1),  # will not be expired
        ]
        self.expires = expires  # Save for comparisons in the tests

        for expiry in expires:
            token = OAuthToken(
                client_id=client.client_id,
                user_id=u.id,
                access_token=gen_salt(20),
                refresh_token=gen_salt(20),
                expires=expiry,
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
        )
        return app


    def test_token_cleanup(self):
        """
        Tests that expires oauth2tokens are properly removed from the database
        as a result of the procedure
        """
        original_tokens = db.session.query(OAuthToken).all()
        self.assertItemsEqual(
            [i.expires for i in original_tokens],
            self.expires
        )

        cleanup_tokens(app=self.app)
        current_tokens = db.session.query(OAuthToken).all()
        self.assertNotEqual(original_tokens, current_tokens)
        self.assertEqual(2, len(current_tokens))
        self.assertEqual(
            [i.expires for i in current_tokens],
            [i for i in self.expires if i >= datetime.datetime.now()],
        )

        time.sleep(3)  # Sleep to let one token expire

        cleanup_tokens(app=self.app)
        current_tokens = db.session.query(OAuthToken).all()
        self.assertNotEqual(original_tokens, current_tokens)
        self.assertEqual(1, len(current_tokens))
        self.assertEqual(
            [i.expires for i in current_tokens],
            [i for i in self.expires if i >= datetime.datetime.now()],
        )







TEST_SUITE = make_test_suite(TestManage_Accounts)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)