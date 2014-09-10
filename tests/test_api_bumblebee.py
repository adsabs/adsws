from tests.api_base import ApiTestCase
from flask import url_for
from adsws.testsuite import make_test_suite, run_test_suite
import httpretty
import json

class TestBumbleBee(ApiTestCase):
    
    @httpretty.activate
    def test_bootstrap(self):
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

        
        r = self.client.get(url_for('api_bumblebee.bootstrap'))
        data = json.loads(r.data)
        self.assertTrue('access_key' in data)
        self.assertTrue('expire_in' in data)
        self.assertEqual(data['username'], 'anonymous')
        
        headers = {'Authorization: %s' % data['access_token']}
        r = self.client.get(url_for('api_solr.search'), headers=headers)
        self.assertTrue('responseHeader' in json.loads(r.data))
        

TESTSUITE = make_test_suite(TestBumbleBee)

if __name__ == '__main__':
    run_test_suite(TESTSUITE)