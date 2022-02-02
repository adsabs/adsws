# -*- coding: utf-8 -*-

from oauthlib.oauth2.rfc6749.errors import InsecureTransportError, \
    InvalidRedirectURIError
from wtforms_alchemy import model_form_factory
from wtforms import fields, validators, widgets
from adsws.utils.forms import AdsWSBaseForm

from .models import OAuthClient


#
# Widget
#
def scopes_multi_checkbox(field, **kwargs):
    """ Render multi checkbox widget. """
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)

    html = ['<div class="row">']

    for value, label, checked in field.iter_choices():
        choice_id = '%s-%s' % (field_id, value)

        options = dict(
            kwargs,
            name=field.name,
            value=value,
            id=choice_id,
            class_=' ',
        )

        if checked:
            options['checked'] = 'checked'

        html.append('<div class="col-md-3">')
        html.append('<label for="%s" class="checkbox-inline">' % field_id)
        html.append('<input %s /> ' % widgets.html_params(**options))
        html.append("%s <br/><small class='text-muted'>%s</small>" % (
            value, label.help_text)
        )
        html.append('</label></div>')
    html.append('</div>')

    return ''.join(html)


#
# Redirect URI field
#
class RedirectURIField(fields.TextAreaField):

    """ Process redirect URI field data. """

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = "\n".join([
                x.strip() for x in
                [x for x in "\n".join(valuelist).splitlines() if x]
            ])

    def process_data(self, value):
        self.data = "\n".join(value)


class RedirectURIValidator(object):

    """ Validate if redirect URIs. """

    def __call__(self, form, field):
        errors = []
        for v in field.data.splitlines():
            try:
                OAuthClient.validate_redirect_uri_form(v)
            except InsecureTransportError:
                errors.append(v)
            except InvalidRedirectURIError:
                errors.append(v)

        if errors:
            raise validators.ValidationError(
                "Invalid redirect URIs: %s" % ", ".join(errors)
            )


#
# Forms
#
class ClientFormBase(model_form_factory(AdsWSBaseForm)):
    class Meta:
        model = OAuthClient
        exclude = [
            'client_secret',
            'is_internal',
            'is_confidential',
        ]
        strip_string_fields = True
        field_args = dict(website=dict(
            validators=[validators.InputRequired(), validators.URL()],
            widget=widgets.TextInput(),
        ))


class OAuthClientForm(ClientFormBase):
    # Trick to make redirect_uris render in the bottom of the form.
    redirect_uris = RedirectURIField(
        label="Redirect URIs (one per line)",
        description="One redirect URI per line. This is your applications"
                    " authorization callback URLs. HTTPS must be used for all "
                    "hosts except localhost (for testing purposes).",
        validators=[RedirectURIValidator(), validators.InputRequired()],
        default='',
    )


class OAuthTokenForm(AdsWSBaseForm):
    name = fields.TextAreaField(
        description="Name of personal access token.",
        validators=[validators.InputRequired()],
    )
    scopes = fields.SelectMultipleField(
        widget=scopes_multi_checkbox,
        choices=[],  # Must be dynamically provided in view.
        description="Scopes assigns permissions to your personal access token."
                    " A personal access token works just like a normal OAuth "
                    " access token for authentication against the API."
    )
