from tests.api_base import ApiTestCase
from flask import url_for
from adsws.testsuite import make_test_suite, run_test_suite
import httpretty
import json

class TestSolr(ApiTestCase):
    
    @httpretty.activate
    def test_sanitization(self):
        def request_callback(request, uri, headers):
            if 'body' in request.parsed_body['fl'][0]:
                return (500, headers, "The query was not sanitized properly")
            return (200, headers, "The {} response from {}".format(request.method, uri))
    
        httpretty.register_uri(
            httpretty.POST, self.app.config.get('SOLR_SEARCH_HANDLER'),
            body=request_callback)
        
        resp = self.remote_client.get(url_for('api_solr.search'),
                    data={'q': 'star', 'fl': 'body,title'})
        self.assertEqual(resp.status, 200)
        
    
    @httpretty.activate
    def test_access(self):
        httpretty.register_uri(
                httpretty.POST, self.app.config.get('SOLR_SEARCH_HANDLER'),
                content_type='application/json',
                status=200,
                body="""{
                "responseHeader":{
                "status":0, "QTime":0,
                "params":{ "fl":"title,bibcode", "indent":"true", "wt":"json", "q":"*:*"}},
                "response":{"numFound":10456930,"start":0,"docs":[
                  { "bibcode":"2005JGRC..110.4002G" },
                  { "bibcode":"2005JGRC..110.4003N" },
                  { "bibcode":"2005JGRC..110.4004Y" }]}}""")

        resp = self.remote_client.get(url_for('api_solr.search'))
        self.assertEqual(resp.status, 200)
        self.assertTrue('responseHeader' in json.loads(resp.data))

TESTSUITE = make_test_suite(TestSolr)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)