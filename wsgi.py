# -*- coding: utf-8 -*-
"""
    wsgi
    ~~~~

    adsws wsgi module
"""
from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from adsws import feedback
from adsws import accounts
from adsws import api
from adsws import frontend
from adsws import benchmark

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
BENCHMARK = dict(mount='/benchmark', app=benchmark.create_app())

resources = get_resources(API, ACCOUNTS, FEEDBACK)

application = DispatcherMiddleware(frontend.create_app(resources=resources), {
    API['mount']: API['app'],
    ACCOUNTS['mount']: ACCOUNTS['app'],
    FEEDBACK['mount']: FEEDBACK['app'],
    BENCHMARK['mount']: BENCHMARK['app'],
})

if __name__ == "__main__":
    run_simple('0.0.0.0', 5000, application, use_reloader=False, use_debugger=True)
