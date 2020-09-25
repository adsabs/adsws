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
FORM_SLACK_EMOJI = ':inbox_tray:'
DEFAULT_EMAIL = 'adshelp@cfa.harvard.edu'
# Feedback processing depends on 'origin' attribute supplied in POST data
FEEDBACK_FORMS_ORIGIN = 'user_submission'
BBB_FEEDBACK_ORIGIN = 'bbb_feedback'
# Email template to be applied based on email subject
FEEDBACK_TEMPLATES = {
    'Missing References': 'missing_references.txt',
    'Associated Articles': 'associated_articles.txt',
    'Updated Record': 'updated_record.txt',
    'New Record': 'new_record.txt',
    'Bumblebee Feedback':'bumblebee_feedback.txt'
}
# Override defaul recipient based on email subject (key)
FEEDBACK_EMAILS = {
    'Missing References': 'ads@cfa.harvard.edu',
}

GOOGLE_RECAPTCHA_ENDPOINT = 'https://www.google.com/recaptcha/api/siteverify'
GOOGLE_RECAPTCHA_PRIVATE_KEY = 'MY_PRIVATE_KEY'
CORS_DOMAINS = ['https://ui.adsabs.harvard.edu']
CORS_HEADERS = []
CORS_METHODS = ['POST', 'GET']

