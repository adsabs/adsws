# -*- coding: utf-8 -*-


from wtforms_alchemy import model_form_factory
from wtforms import fields, validators, widgets
from adsws.utils.forms import AdsWSBaseForm

from .models import Client

ModelForm = model_form_factory(AdsWSBaseForm)


class ClientForm(ModelForm):
    class Meta:
        model = Client
        exclude = [
            'client_secret',
            'is_internal',
            'is_confidential',
        ]
        strip_string_fields = True
        field_args = dict(website=dict(
            validators=[validators.Required(), validators.URL()],
            widget=widgets.TextInput(),
        ))


class TokenForm(AdsWSBaseForm):
    name = fields.TextField(
        description="Name of personal access token.",
        validators=[validators.Required()],
    )
    #scopes = fields.SelectMultipleField()
