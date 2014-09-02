from flask_mail import Mail

# In case you wonder why we have two extensions: Flask-Mail, and Flask-Email
# then know that it is because Flask-Security is using Flask-Mail, but we
# want to use Flask-Email (it allows for flexible backends). Thus, if the 
# Flask-Email is loaded by your application our security will use that instead 
# of the default Flask-Mail

#: Flask-Mail extension instance
mail = Mail()

def setup_app(app):
    """
    Prepare email extension

    :see: https://flask-email.readthedocs.org/en/latest/#configuration
    """
    
    mail.init_app(app)
    
    return app