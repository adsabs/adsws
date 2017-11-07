import time
import json
import requests
from flask.ext.restful import Resource
from adsws.core import db
from adsws.ext.ratelimiter import ratelimit, scope_func
from flask import request
from sqlalchemy import text

def get_post_data(request):
    """
    Attempt to coerce POST json data from the request, falling
    back to the raw data if json could not be coerced.
    :param request: flask.request
    """
    try:
        post_data = request.get_json(force=True)
    except:
        post_data = request.values

    post_data = dict(post_data)
    return post_data

class ApiEndView(Resource):
    """
    View that returns a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def post(self):
        """
        POST response
        """
        post_data = get_post_data(request)
        sleep = post_data.get('sleep', 0)
        start_time = time.gmtime().tm_sec
        time.sleep(sleep)

        post_data['last_sent'] = 'benchmark/api/end'
        post_data['sent_from'].append('benchmark/api/end')
        post_data['service'] = {
            'received_time': start_time,
            'sleep': sleep
        }

        sql = text("SELECT pg_sleep({});".format(sleep))
        result = db.session.execute(sql)

        return post_data, 200

class ApiRedirectView(Resource):
    """
    View that contacts a second service which will return a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def post(self):

        post_data = get_post_data(request)
        post_data['last_sent'] = 'benchmark/api/redirect'
        post_data['sent_from'].append('benchmark/api/redirect')

        if 'sleep' not in post_data:
            post_data['sleep'] = 0

        # Post to the end point
        r = requests.post(
            'http://localhost/benchmark/api/end',
            data=json.dumps(post_data)
        )

        # Get the response content if there was no failure
        try:
            _json = r.json()
        except:
            _json = {'msg': r.text}

        return _json, r.status_code

class ApiDoubleRedirectView(Resource):
    """
    View that contacts a second service that will contact the API and
    return a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def post(self):

        post_data = get_post_data(request)
        post_data['last_sent'] = 'benchmark/api/double_redirect'
        post_data['sent_from'].append('benchmark/api/double_redirect')

        if 'sleep' not in post_data:
            post_data['sleep'] = 0

        store_in_db(post_data) # INSERT in PostgreSQL without forced sleep

        # Post to the next point
        r = requests.post(
            'http://localhost/benchmark/api/redirect',
            data=json.dumps(post_data)
        )

        # Get the response content if there was no failure
        try:
            _json = r.json()
        except:
            _json = {'msg': r.text}

        return _json, r.status_code
