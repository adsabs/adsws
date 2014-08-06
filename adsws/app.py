import requests
import os

from urllib import urlencode

from flask import Flask
from flask import request

app = Flask(__name__)
app.config.from_object('settings')
app.config.from_envvar('ADSWS_SETTINGS_PATH')


@app.route('/api/1/search', methods=['GET', 'POST'])
def api_search():
    
    headers = request.headers
    
    if request.method == 'POST':
        payload = dict(request.form)
    else:
        payload = dict(request.args)
        
    payload['wt'] = 'json'
    if 'fl' not in payload:
        payload['fl'] = 'id'
    
    headers = dict(headers.items())
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    r = requests.post(app.config['SOLR_URL'], data=urlencode(payload, doseq=True), headers=headers)
    return r.text
