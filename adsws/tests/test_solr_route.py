from unittest import TestCase
from adsws.api.discoverer import solr_route
from flask.ext.restful import Resource
import flask
from flask_restful import Resource, Api
import mock

class SetCookieView(Resource):
    """
    Returns a good HTTP answer with a coockie set in the headers
    """
    storage = None
    solr_route_cookie_name = "sroute"
    solr_route_redis_prefix = "token:sroute:test"
    solr_route_redis_expiration_time = 3600
    @solr_route.solr_route(storage, solr_route_cookie_name, solr_route_redis_prefix, solr_route_redis_expiration_time)
    def get(self):
        return {}, 200, {'Set-Cookie': 'sroute=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; Path=/; HttpOnly'}

class DontSetCookieView(Resource):
    """
    Returns a good HTTP answer without any coockie set in the headers
    """
    storage = None
    solr_route_cookie_name = "sroute"
    solr_route_redis_prefix = "token:sroute:test"
    solr_route_redis_expiration_time = 3600
    @solr_route.solr_route(storage, solr_route_cookie_name, solr_route_redis_prefix, solr_route_redis_expiration_time)
    def get(self):
        return {}, 200, {}


class SolrRouteTestCase(TestCase):
    """
    Tests solr route decorator
    """

    def setUp(self):
        super(self.__class__, self).setUp()
        app = flask.Flask(__name__)
        api = Api(app)
        api.add_resource(SetCookieView, '/set_cookie')
        api.add_resource(DontSetCookieView, '/dont_set_cookie')
        self.app = app.test_client()


    def tearDown(self):
        super(self.__class__, self).tearDown()


    def test_set_cookie(self):
        """
        Test that the cookie is set
        """
        solr_route._get_solr_route = mock.Mock(return_value="zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        solr_route._set_solr_route = mock.Mock()
        rv = self.app.get('/set_cookie', headers=[['Authorization', "Bearer:TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"]])
        self.assertIn('Set-Cookie', rv.headers)
        self.assertEquals(rv.headers['Set-Cookie'], 'sroute=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; Path=/; HttpOnly')
        solr_route._get_solr_route.assert_called_once()
        solr_route._set_solr_route.assert_called_once()


    def test_set_cookie(self):
        """
        Test that no cookie is set
        """
        solr_route._get_solr_route = mock.Mock(return_value=None)
        solr_route._set_solr_route = mock.Mock()
        rv = self.app.get('/dont_set_cookie', headers=[['Authorization', "Bearer:TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"]])
        self.assertNotIn('Set-Cookie', rv.headers)
        solr_route._get_solr_route.assert_called_once()
        solr_route._set_solr_route.assert_not_called()

