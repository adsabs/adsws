from flask import session, current_app
from flask.ext.wtf import Form
from wtforms.ext.csrf.session import SessionSecureForm

class AdsWSBaseForm(Form, SessionSecureForm):
    #SECRET_KEY = CFG_SITE_SECRET_KEY
    TIME_LIMIT = 1200.0

    def __init__(self, *args, **kwargs):
        super(AdsWSBaseForm, self).__init__(
            *args, csrf_context=session, **kwargs
        )

    def add_fields(self, name, field):
        self.__setattr__(name, field)

    def validate_csrf_token(self, field):
        # Disable CRSF proection during testing
        if current_app.testing:
            return
        super(AdsWSBaseForm, self).validate_csrf_token(field)