# -*- coding: utf-8 -*-


from wtforms_alchemy import model_form_factory
from wtforms import fields, validators, widgets
from adsws.utils.forms import AdsWSBaseForm

from .models import OAuthClient

ModelForm = model_form_factory(AdsWSBaseForm)


class OAuthClientForm(ModelForm):
    class Meta:
        model = OAuthClient
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


class OAuthTokenForm(AdsWSBaseForm):
    name = fields.TextField(
        description="Name of personal access token.",
        validators=[validators.Required()],
    )
    #scopes = fields.SelectMultipleField()
