"""
Configuration file. Please prefix application specific config values with
the application name.
"""
LOG_LEVEL = 30 # To be deprecated when all microservices use ADSFlask
LOGGING_LEVEL = "INFO"
LOG_STDOUT = True
EXTENSIONS = [
    'adsws.ext.ratelimiter',
    'adsws.ext.mail'
]

FEEDBACK_SLACK_END_POINT = 'https://hooks.slack.com/services/TOKEN/TOKEN'
FEEDBACK_SLACK_EMOJI = ':interrobang:'
FEEDBACK_EMAIL = 'adshelp@cfa.harvard.edu'
GOOGLE_RECAPTCHA_ENDPOINT = 'https://www.google.com/recaptcha/api/siteverify'
GOOGLE_RECAPTCHA_PRIVATE_KEY = 'MY_PRIVATE_KEY'
CORS_DOMAINS = ['https://ui.adsabs.harvard.edu']
CORS_HEADERS = []
CORS_METHODS = ['POST', 'GET']
