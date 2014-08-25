PASSWORD_LEN_MIN = 6
PASSWORD_LEN_MAX = 250
USERNAME_LEN_MIN = 1
USERNAME_LEN_MAX = 250

# http://pythonhosted.org/Flask-Security/configuration.html
SECURITY_CONFIRMABLE = False
SECURITY_REGISTERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_PASSWORDLESS = False
SECURITY_RECOVERABLE = True


# https://flask-email.readthedocs.org/en/latest/#
EMAIL_BACKEND='flask.ext.email.backends.console.Mail'

# Flask-mail: http://pythonhosted.org/flask-mail/
# https://bitbucket.org/danjac/flask-mail/issue/3/problem-with-gmails-smtp-server
MAIL_DEBUG = False
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
# Should put MAIL_USERNAME and MAIL_PASSWORD in production under instance folder.
MAIL_USERNAME = 'admin@adws.com'
MAIL_PASSWORD = 'password'
MAIL_DEFAULT_SENDER = MAIL_USERNAME