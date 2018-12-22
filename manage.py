# -*- coding: utf-8 -*-
"""
    manage
    ~~~~~~

    Manager module
"""

import os
import flask
from flask.ext.script import Manager
from adsws.accounts.manage import accounts_manager

manager = Manager(flask.Flask('manager'))

manager.add_command("accounts", accounts_manager)

@manager.command
def generate_secret_key():
    """
    Generate a random string suitable for using a the SECRET_KEY value
    """
    key = "'{0}{1}'".format(os.urandom(15), os.urandom(15))
    print "\nSECRET_KEY = '{0}'\n".format(key.encode('hex'))


@manager.shell
def make_shell_context():
    from wsgi import application, API, ACCOUNTS
    app = application.app
    context = app.app_context()
    flask._app_ctx_stack.push(context)


    return dict(app=app, api=API, accounts=ACCOUNTS,
                context=context)

if __name__ == "__main__":
    manager.run()