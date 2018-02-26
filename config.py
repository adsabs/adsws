
#flask Setting for debug view in case of errors
DEBUG = False
#Flask setting for unittest (be sure this value is FALSE on real site!)
TESTING = False

# Be careful; if using sqlite AND the path is relative
# then each application can get a different database
# e.g. if you have 'sqlite:///adsws.sqlite' then the
# db will be saved at adsws/api/adsws.sqlite
SQLALCHEMY_DATABASE_URI = 'sqlite://'
SITE_SECURE_URL = 'http://0.0.0.0:5000'

# Flask session config (http://flask.pocoo.org/docs/0.12/config/)
PERMANENT_SESSION_LIFETIME = 3600*24*365.25 # 1 year in seconds
SESSION_REFRESH_EACH_REQUEST = True
