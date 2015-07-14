"""
Configuration file. Please prefix application specific config values with
the application name.
"""
EXTENSIONS = [
    'adsws.ext.ratelimiter'
]

# These values are necessary only if the app needs to be a client of the API
SAMPLE_APPLICATION_ADSWS_API_TOKEN = 'this is a secret api token!'
SAMPLE_APPLICATION_ADSWS_API_URL = 'https://api.adsabs.harvard.edu'
FEEDBACK_SLACK_END_POINT = 'https://hooks.slack.com/services/TOKEN/TOKEN'
GOOGLE_RECAPTCHA_ENDPOINT = 'https://www.google.com/recaptcha/api/siteverify'
GOOGLE_RECAPTCHA_PRIVATE_KEY = 'MY_PRIVATE_KEY'
