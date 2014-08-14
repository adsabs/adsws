import requests
from flask import Blueprint, request
from flask import current_app
from urllib import urlencode

from . import route
bp = Blueprint('search', __name__)

@route(bp, '/search', methods=['GET'])
def search():
    """Searches SOLR."""
    headers = request.headers
    payload = dict(request.args)
    payload = cleanup_solr_request(payload)
    
    headers = dict(headers.items())
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    r = requests.post(current_app.config.get('SOLR_SEARCH_HANDLER'), data=urlencode(payload, doseq=True), headers=headers)
    return r.text, r.status_code

    
def cleanup_solr_request(payload):
    payload['wt'] = 'json'
    # we disallow 'return everything'
    if 'fl' not in payload:
        payload['fl'] = 'id'
    return payload