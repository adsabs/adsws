# In case you wonder why we have two extensions: Flask-Mail, and Flask-Email
# then know that it is because Flask-Security is using Flask-Mail, but we
# want to use Flask-Email (it allows for flexible backends). Thus, if the 
# Flask-Email is loaded by your application our security will use that instead 
# of the default Flask-Mail

from jinja2.utils import import_string

def setup_app(app):
    backend = app.config.get('EMAIL_BACKEND', 'flask_email:ConsoleMail')
    module = import_string(backend)
    backimpl = module()
    backimpl.init_app(app)
    if 'email' not in app.extensions:
        app.extensions['email'] = backimpl
    return app