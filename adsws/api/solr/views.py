import requests
from flask import Blueprint, request
from flask import current_app
from urllib import urlencode

from .. import route

from adsws.modules.oauth2server.provider import oauth2

blueprint = Blueprint('api_solr', __name__)

@route(blueprint, '/search', methods=['GET'])
@oauth2.require_oauth('api:search')
def search():
    """Searches SOLR."""
    headers = request.headers
    payload = dict(request.args)
    payload = cleanup_solr_request(payload)
    
    headers = dict(headers.items())
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    r = requests.post(current_app.config.get('SOLR_SEARCH_HANDLER'), 
                      data=urlencode(payload, doseq=True), headers=headers)
    return r.text, r.status_code

@route(blueprint, '/qtree', methods=['GET'])
@oauth2.require_oauth('api:search')
def qtree():
    """Retursn parse query tree."""
    headers = request.headers
    payload = dict(request.args)
    payload = cleanup_solr_request(payload)
    
    headers = dict(headers.items())
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    r = requests.post(current_app.config.get('SOLR_QTREE_HANDLER'), 
                      data=urlencode(payload, doseq=True), headers=headers)
    return r.text, r.status_code
    
def cleanup_solr_request(payload):
    payload['wt'] = 'json'
    # we disallow 'return everything'
    if 'fl' not in payload:
        payload['fl'] = 'id'
    else:
        disallowed = {'body':1, 'full': 1}
        fields = payload['fl'][0].split(',')
        fields = filter(lambda x: x not in disallowed, fields)
        if len(fields) == 0:
            fields.append('id')
        payload['fl'][0] = ','.join(fields)
    return payload