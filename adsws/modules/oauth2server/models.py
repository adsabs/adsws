# -*- coding: utf-8 -*-



from flask import current_app
from flask_login import current_user
from werkzeug.security import gen_salt
from wtforms import validators
from sqlalchemy_utils import URLType

from adsws.core import db, user_manipulator
from adsmutils import get_date, UTCDateTime
from authlib.integrations.sqla_oauth2 import OAuth2ClientMixin, OAuth2TokenMixin
from oauthlib.oauth2.rfc6749.errors import InsecureTransportError, InvalidRedirectURIError
import six
from six.moves.urllib_parse import urlparse

class OAuthUserProxy():
    """
    Proxy object to the User object; it is stored in the 
    cache and identifies the user who started the OAuth flow.
    """
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        """ Pass any undefined attribute to the underlying object """
        return getattr(self._user, name)

    def __getstate__(self):
        return self.id

    def __setstate__(self, state):
        self._user = user_manipulator.get(state)

    @property
    def id(self):
        return self._user.get_id()

    def check_password(self, password):
        return self.password == password

    @classmethod
    def get_current_user(cls):
        return cls(current_user._get_current_object())



class Scope(object):
    def __init__(self, id_, help_text='', group='', internal=False):
        self.id = id_
        self.group = group
        self.help_text = help_text
        self.is_internal = internal
        

class OAuthClient(db.Model, OAuth2ClientMixin):
    """
    A client is the app which want to use the resource of a user. It is
    suggested that the client is registered by a user on your site, but it
    is not required.

    The client should contain at least these information:

        client_id: A random string
        client_secret: A random string
        client_type: A string represents if it is confidential
        redirect_uris: A list of redirect uris
        default_redirect_uri: One of the redirect uris
        default_scopes: Default scopes of the client

    But it could be better, if you implemented:

        allowed_grant_types: A list of grant types
        allowed_response_types: A list of response types
        validate_scopes: A function to validate scopes

    """

    __tablename__ = 'oauth2client'

    name = db.Column(
        db.String(40),
        info=dict(
            label='Name',
            description='Name of application (displayed to users).',
            validators=[validators.DataRequired()]
        )
    )
    """ Human readable name of the application. """

    description = db.Column(
        db.Text(),
        default='',
        info=dict(
            label='Description',
            description='Optional. Description of the application'
                        ' (displayed to users).',
        )
    )
    """ Human readable description. """

    website = db.Column(
        URLType(),
        info=dict(
            label='Website URL',
            description='URL of your application (displayed to users).',
        ),
        default='',
    )

    user_id = db.Column(db.ForeignKey('users.id'))
    """ Creator of the client application. """

    client_id = db.Column(db.String(255), primary_key=True)
    """ Client application ID. """

    client_secret = db.Column(
        db.String(255), unique=True, index=True, nullable=False
    )
    """ Client application secret. """

    is_confidential = db.Column(db.Boolean, default=True)
    """ Determine if client application is public or not.  """

    is_internal = db.Column(db.Boolean, default=False)
    """ Determins if client application is an internal application. """

    last_activity = db.Column(db.DateTime, nullable=True)
    """ Datetime that stores the last time this client was accessed. """

    _redirect_uris = db.Column(db.Text)
    """A newline-separated list of redirect URIs. First is the default URI."""

    _default_scopes = db.Column(db.Text)
    """A space-separated list of default scopes of the client.

    The value of the scope parameter is expressed as a list of space-delimited,
    case-sensitive strings.
    """

    user = db.relationship('User')
    """ Relationship to user. """
    
    ratelimit = db.Column(db.Float, default=0.0)
    """ Pre-computed allotment of the available rates of the user's global ratelimit."""
    
    created = db.Column(UTCDateTime, default=get_date)
    
    @property
    def allowed_grant_types(self):
        return current_app.config['OAUTH2_ALLOWED_GRANT_TYPES']

    @property
    def allowed_response_types(self):
        return current_app.config['OAUTH2_ALLOWED_RESPONSE_TYPES']

    # def validate_scopes(self, scopes):
    #     return self._validate_scopes

    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.splitlines()
        return []

    @redirect_uris.setter
    def redirect_uris(self, value):
        """ Validate and store redirect URIs for client. """
        if isinstance(value, six.text_type):
            value = value.split("\n")

        value = [v.strip() for v in value]

        for v in value:
            self.validate_redirect_uri_form(v)

        self._redirect_uris = "\n".join(value) or ""

    
    
    @staticmethod
    def validate_redirect_uri_form(value):
        """ Validate a redirect URI.

        A redirect URL must utilize https or redirect to localhost.

        :param value: Value to validate.
        :raises: InvalidRedirectURIError, InsecureTransportError
        """
        sch, netloc, path, par, query, fra = urlparse(value)
        if not (sch and netloc):
            raise InvalidRedirectURIError()
        if sch != 'https':
            if ':' in netloc:
                netloc, port = netloc.split(':', 1)
            if not (netloc in ('localhost', '127.0.0.1') and sch == 'http'):
                raise InsecureTransportError()
        return True

    @property
    def default_redirect_uri(self):
        try:
            return self.redirect_uris[0]
        except IndexError:
            pass

    @property
    def default_scopes(self):
        """ List of default scopes for client. """
        if self._default_scopes:
            return self._default_scopes.split(" ")
        return []

    def validate_scopes(self, scopes):
        """ Validate if client is allowed to access scopes. """
        from .registry import scopes as scopes_registry

        for s in set(scopes):
            if s not in scopes_registry:
                return False
        return True

    def gen_salt(self):
        self.reset_client_id()
        self.reset_client_secret()

    def reset_client_id(self):
        self.client_id = gen_salt(
            current_app.config.get('OAUTH2_CLIENT_ID_SALT_LEN')
        )

    def reset_client_secret(self):
        self.client_secret = gen_salt(
            current_app.config.get('OAUTH2_CLIENT_SECRET_SALT_LEN')
        )

class OAuthToken(db.Model, OAuth2TokenMixin):
    """
    A bearer token is the final token that can be used by the client.
    """
    __tablename__ = 'oauth2token'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    """ Object ID """

    client_id = db.Column(
        db.String(40), db.ForeignKey('oauth2client.client_id', ondelete='CASCADE'),
        nullable=False,
    )
    """ Foreign key to client application """

    client = db.relationship('OAuthClient', backref=db.backref('oauth2client', passive_deletes=True))
    """ SQLAlchemy relationship to client application """

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE')
    )
    """ Foreign key to user """

    user = db.relationship('User')
    """ SQLAlchemy relationship to user """

    token_type = db.Column(db.String(255), default='bearer')
    """ Token type - only bearer is supported at the moment """

    access_token = db.Column(db.String(255), unique=True)

    refresh_token = db.Column(db.String(255), unique=True)

    expires = db.Column(db.DateTime, nullable=True)

    _scopes = db.Column(db.Text)

    is_personal = db.Column(db.Boolean, default=False)
    """ Personal accesss token """

    is_internal = db.Column(db.Boolean, default=False)
    """ Determines if token is an internally generated token. """

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []

    @classmethod
    def create_personal(cls, name, user_id, scopes=None, is_internal=False):
        """
        Create a personal access token (a token that is bound to a specific
        user and which doesn't expire).
        """
        scopes = " ".join(scopes) if scopes else ""

        c = OAuthClient(
            name=name,
            user_id=user_id,
            is_internal=True,
            is_confidential=False,
            _default_scopes=scopes
        )
        c.gen_salt()

        t = OAuthToken(
            client_id=c.client_id,
            user_id=user_id,
            access_token=gen_salt(
                current_app.config.get('OAUTH2_TOKEN_PERSONAL_SALT_LEN', 40)
            ),
            expires=None,
            _scopes=scopes,
            is_personal=True,
            is_internal=is_internal,
        )

        db.session.add(c)
        db.session.add(t)
        db.session.commit()

        return t

class OAuthGrant(db.Model):
    """
    A grant token is created in the authorization flow, 
    and will be destroyed when the authorization finished.
    """
     
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    client_id = db.Column(
        db.String(40), db.ForeignKey('oauth2client.client_id'),
        nullable=False,
    )
    client = db.relationship('OAuthClient')

    code = db.Column(db.String(255), index=True, nullable=False)

    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)

    _scopes = db.Column(db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []

__all__ = ['OAuthClient',
           'OAuthToken',
           'OAuthGrant']