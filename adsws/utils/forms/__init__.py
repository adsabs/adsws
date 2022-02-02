from flask import session, current_app
from flask_wtf import Form

class AdsWSBaseForm(Form):
    #SECRET_KEY = CFG_SITE_SECRET_KEY
    TIME_LIMIT = 1200.0

    def __init__(self, *args, **kwargs):
        super(AdsWSBaseForm, self).__init__(
            *args, csrf_context=session, **kwargs
        )

    def add_fields(self, name, field):
        self.__setattr__(name, field)
