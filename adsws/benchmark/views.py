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

class BenchmarkEndView(Resource):
    """
    View that returns a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def post(self):
        """
        POST response
        """
        start_time = time.gmtime().tm_sec
        post_data = get_post_data(request)
        post_data['last_sent'] = 'benchmark/end'
        post_data['sent_from'].append('benchmark/end')
        post_data['service'] = {
            'received_time': start_time,
        }

        if 'sleep' not in post_data:
            post_data['sleep'] = 0

        sql = text("SELECT datid, datname, pid, usename, client_addr, state, query FROM pg_stat_activity, pg_sleep({}) where datname = 'adsws';".format(post_data['sleep']))
        result = db.session.execute(sql)

        return post_data, 200

class BenchmarkRedirectView(Resource):
    """
    View that contacts a second service which will return a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def post(self):

        post_data = get_post_data(request)
        post_data['last_sent'] = 'benchmark/redirect'
        post_data['sent_from'].append('benchmark/redirect')

        if 'sleep' not in post_data:
            post_data['sleep'] = 0

        # Post to the end point
        r = requests.post(
            'http://localhost/benchmark/end',
            data=json.dumps(post_data)
        )

        # Get the response content if there was no failure
        try:
            _json = r.json()
        except:
            _json = {'msg': r.text}

        return _json, r.status_code

class BenchmarkDoubleRedirectView(Resource):
    """
    View that contacts a second service that will contact the API and
    return a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def post(self):

        post_data = get_post_data(request)
        post_data['last_sent'] = 'benchmark/double_redirect'
        post_data['sent_from'].append('benchmark/double_redirect')

        if 'sleep' not in post_data:
            post_data['sleep'] = 0

        #sql = text("SELECT datid, datname, pid, usename, client_addr, state, query FROM pg_stat_activity, pg_sleep({}) where datname = 'adsws';".format(post_data['sleep']))
        #result = db.session.execute(sql)

        # Post to the next point
        r = requests.post(
            'http://localhost/benchmark/redirect',
            data=json.dumps(post_data)
        )

        # Get the response content if there was no failure
        try:
            _json = r.json()
        except:
            _json = {'msg': r.text}

        return _json, r.status_code
