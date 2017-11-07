# -*- coding: utf-8 -*-
"""
    wsgi
    ~~~~

    adsws wsgi module
"""
import psycogreen.gevent; psycogreen.gevent.patch_psycopg()
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

from adsws import feedback
from adsws import accounts
from adsws import api
from adsws import frontend
from adsws import benchmark_api

def get_resources(*apps):
    r = {}
    for _container in apps:
        app = _container['app']
        mnt = _container['mount']
        r[app.name] = {}
        r[app.name]['endpoints'] = []
        r[app.name]['base'] = mnt
        for rule in app.url_map.iter_rules():
            r[app.name]['endpoints'].append(rule.rule)
    return r

API = dict(mount='/v1', app=api.create_app())
ACCOUNTS = dict(mount='/v1/accounts', app=accounts.create_app())
FEEDBACK = dict(mount='/v1/feedback', app=feedback.create_app())
BENCHMARK_API = dict(mount='/benchmark/api', app=benchmark_api.create_app())

resources = get_resources(API, ACCOUNTS, FEEDBACK, BENCHMARK_API)

application = DispatcherMiddleware(frontend.create_app(resources=resources), {
    API['mount']: API['app'],
    ACCOUNTS['mount']: ACCOUNTS['app'],
    FEEDBACK['mount']: FEEDBACK['app'],
    BENCHMARK_API['mount']: BENCHMARK_API['app'],
})

if __name__ == "__main__":
    run_simple('0.0.0.0', 5000, application, use_reloader=False, use_debugger=True)
