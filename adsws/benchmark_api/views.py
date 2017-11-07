import time
import json
import requests
from flask.ext.restful import Resource
from adsws.core import db
from adsws.ext.ratelimiter import ratelimit, scope_func
from flask import request

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
    decorators = [ratelimit.shared_limit_and_check("30/120 second", scope=scope_func)] # Flask Limiter

    def post(self):
        """
        POST response
        """
        post_data = get_post_data(request)
        sleep = post_data.get('sleep', 0)
        start_time = time.gmtime().tm_sec
        time.sleep(sleep)

        post_data['last_sent'] = 'benchmark_api/end'
        post_data['sent_from'].append('benchmark_api/end')
        post_data['service'] = {
            'received_time': start_time,
            'sleep': sleep
        }

        from sqlalchemy import text
        sql = text("SELECT pg_sleep(10);")
        result = db.session.execute(sql)

        return post_data, 200


