from flask_mail import Mail

# TODO: add customization here

#: Flask-Mail extension instance
mail = Mail()

def setup_app(app):
    """
    Prepare email extension

    :see: https://flask-email.readthedocs.org/en/latest/#configuration
    """
    
    mail.init_app(app)
    
    return app