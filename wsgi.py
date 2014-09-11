# -*- coding: utf-8 -*-
"""
    wsgi
    ~~~~

    adsws wsgi module
"""

from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

from adsws import root
from adsws import api
from adsws import frontend

application = DispatcherMiddleware(root.create_app(), {
    '/v1': api.create_app(),
    '/ui': frontend.create_app()
})

if __name__ == "__main__":
    run_simple('0.0.0.0', 6002, application, use_reloader=True, use_debugger=True)
