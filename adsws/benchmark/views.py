import time
import json
import requests
from flask.ext.restful import Resource
from adsws.core import db
from adsws.ext.ratelimiter import ratelimit, scope_func
from flask import current_app, request
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

class BenchmarkTimeoutEndView(Resource):
    """
    View that returns a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def get(self):
        """
        GET response
        """
        sleep = request.args.get('sleep', default = 0, type = int)

        one_second = 1
        for i in xrange(sleep):
            current_app.logger.info('Iteration %s - Waiting %s second(s) for a total of %s seconds', i, one_second, sleep)
            sql = text("SELECT datid, datname, pid, usename, client_addr, state, query FROM pg_stat_activity, pg_sleep({}) where datname = 'adsws';".format(one_second))
            result = db.session.execute(sql)

        return {'msg': "Slept during {} seconds!"}, 200

class BenchmarkTimeoutRedirectView(Resource):
    """
    View that contacts a second service which will return a response.
    """
    decorators = [ratelimit.shared_limit_and_check("1000/1 second", scope=scope_func)] # Flask Limiter

    def get(self):
        sleep = request.args.get('sleep', default = 0, type = int)
        timeout = request.args.get('timeout', default = 60, type = int)

        current_app.logger.info('Sending request to timeout_end with a sleep order of %s seconds and a timeout of %s seconds', sleep, timeout)
        # Get the end point
        r = requests.get(
            'http://localhost/benchmark/timeout_end?sleep={}'.format(sleep),
            timeout=timeout,
        )

        # Get the response content if there was no failure
        try:
            _json = r.json()
        except:
            _json = {'msg': r.text}

        return _json, r.status_code

