# -*- coding: utf-8 -*-
"""
    wsgi
    ~~~~

    adsws wsgi module
"""
from flask import Flask

from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

from adsws import accounts
from adsws import api

application = DispatcherMiddleware(Flask('placeholder'), {
    '/v1': api.create_app(),
    '/v1/accounts':accounts.create_app(),
})

if __name__ == "__main__":
    run_simple('0.0.0.0', 5000, application, use_reloader=False, use_debugger=True)
