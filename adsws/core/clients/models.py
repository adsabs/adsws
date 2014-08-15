# -*- coding: utf-8 -*-
"""
    adsws.core.clients
    ~~~~~~~~~~~~~~~~~~~~~

    Models for the clients (users) of AdsWS
"""

from flask_security import UserMixin, RoleMixin
from adsws.ext.sqlalchemy import db

roles_clients = db.Table(
    'roles_clients',
    db.Column('client_id', db.Integer(), db.ForeignKey('clients.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('roles.id')))


class Client(UserMixin, db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    password = db.Column(db.String(120))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    registered_at = db.Column(db.DateTime())

    roles = db.relationship('Role', secondary=roles_clients,
                            backref=db.backref('clients', lazy='dynamic'))
    
    

class Role(RoleMixin, db.Model):
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

