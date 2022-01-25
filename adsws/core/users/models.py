# -*- coding: utf-8 -*-
"""
    adsws.core.users
    ~~~~~~~~~~~~~~~~~~~~~

    Models for the users database
"""
from flask_security import UserMixin, RoleMixin
from adsws.ext.sqlalchemy import db
from sqlalchemy.orm import synonym
from flask_security.utils import encrypt_password, verify_password
from flask import current_app
from citext import CIText

roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('roles.id')))


class User(UserMixin, db.Model):
    """
    Define the user model
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(CIText(), unique=True)
    _password = db.Column(db.String(255), name='password')
    name = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    login_count = db.Column(db.Integer)
    registered_at = db.Column(db.DateTime())
    ratelimit_level = db.Column(db.Integer)
    _allowed_scopes = db.Column(db.Text)

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def _set_password(self, password):
        hashed_password = encrypt_password(password)
        if not isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('UTF-8')
        self._password = hashed_password

    def _get_password(self):
        return self._password
    
    password = synonym(
        '_password',
        descriptor=property(_get_password, _set_password)
    )

    def validate_password(self, password):
        return verify_password(password, self._password)

    def get_id(self):
        """
        flask_login:
        Returns a unicode that uniquely identifies this user, and can be used
        to load the user from the user_loader callback. Note that this must be
        a unicode - if the ID is natively an int or some other type, you will
        need to convert it to unicode.
        """
        return str(self.id)
    
    @property
    def allowed_scopes(self):
        """Returns list of scopes that this user is allowed to request/initialize
        when bootstraping a new OAuth client; for example ads:internal scopes
        should only be given/owned to user accounts that can safely dispense
        with them, but should not be available to other users.
        """
        
        if self._allowed_scopes:
            return self._allowed_scopes.split(' ')
        return current_app.config['USER_DEFAULT_SCOPES']


class Role(RoleMixin, db.Model):
    """
    Define the role model
    """
    __tablename__ = 'roles'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __eq__(self, other):
        return (self.name == other or
                self.name == getattr(other, 'name', None))

    def __ne__(self, other):
        return (self.name != other and
                self.name != getattr(other, 'name', None))

