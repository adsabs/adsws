# -*- coding: utf-8 -*-

from flask import Markup

from flask.ext.wtf import Form
from wtforms import (ValidationError, HiddenField, BooleanField, TextField,
        PasswordField, SubmitField)
from wtforms.validators import Required, Length, EqualTo, Email
from flask.ext.wtf.html5 import EmailField

from adsws.core import user_manipulator
from flask import current_app


class LoginForm(Form):
    next = HiddenField()
    login = TextField(u'Username or email', [Required()])
    password = PasswordField('Password', [Required(), Length(current_app.config.get('PASSWORD_LEN_MIN', 1), current_app.config.get('PASSWORD_LEN_MAX', 250))])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign in')


class SignupForm(Form):
    next = HiddenField()
    email = EmailField(u'Email', [Required(), Email()],
            description=u"What's your email address?")
    password = PasswordField(u'Password', [Required(), Length(current_app.config.get('PASSWORD_LEN_MIN', 1), current_app.config.get('PASSWORD_LEN_MAX', 250))],
            description=u'%s characters or more! Be tricky.' % current_app.config.get('PASSWORD_LEN_MIN', 1))
    name = TextField(u'Choose your username', [Required(), Length(current_app.config.get('USERNAME_LEN_MIN', 1), current_app.config.get('USERNAME_LEN_MAX', 250))],
            description=u"You can change it later.")
    agree = BooleanField(u'Agree to the ' +
        Markup('<a target="blank" href="/terms">Terms of Service</a>'), [Required()])
    submit = SubmitField('Sign up')

    def validate_name(self, field):
        if user_manipulator.first(name=field.data) is not None:
            raise ValidationError(u'This username is taken')

    def validate_email(self, field):
        if user_manipulator.first(email=field.data) is not None:
            raise ValidationError(u'This email is taken')


class RecoverPasswordForm(Form):
    email = EmailField(u'Your email', [Email()])
    submit = SubmitField('Send instructions')


class ChangePasswordForm(Form):
    activation_key = HiddenField()
    password = PasswordField(u'Password', [Required()])
    password_again = PasswordField(u'Password again', [EqualTo('password', message="Passwords don't match")])
    submit = SubmitField('Save')


class ReauthForm(Form):
    next = HiddenField()
    password = PasswordField(u'Password', [Required(), Length(current_app.config.get('PASSWORD_LEN_MIN', 1), current_app.config.get('PASSWORD_LEN_MAX', 250))])
    submit = SubmitField('Reauthenticate')


class OpenIDForm(Form):
    openid = TextField(u'Your OpenID', [Required()])
    submit = SubmitField(u'Log in with OpenID')


class CreateProfileForm(Form):
    openid = HiddenField()
    name = TextField(u'Choose your username', [Required(), Length(current_app.config.get('USERNAME_LEN_MIN', 1), current_app.config.get('USERNAME_LEN_MAX', 250))],
            description=u"You can change it later.")
    email = EmailField(u'Email', [Required(), Email()], description=u"What's your email address?")
    password = PasswordField(u'Password', [Required(), Length(current_app.config.get('PASSWORD_LEN_MIN', 1), current_app.config.get('PASSWORD_LEN_MAX', 250))],
            description=u'%s characters or more! Be creative.' % current_app.config.get('PASSWORD_LEN_MIN', 1))
    submit = SubmitField(u'Create Profile')

    def validate_name(self, field):
        if user_manipulator.first(name=field.data) is not None:
            raise ValidationError(u'The username which you select not available.')

    def validate_email(self, field):
        if user_manipulator.first(email=field.data) is not None:
            raise ValidationError(u'The email which you select not available.')
