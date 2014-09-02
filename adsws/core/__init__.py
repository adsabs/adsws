# -*- coding: utf-8 -*-
"""
    adsws.core
    ~~~~~~~~~~~~~

    core module: loaded by every app that runs in ADSWS container
"""



from ..ext.mail import mail
from ..ext.sqlalchemy import db

from .errors import AdsWSError, AdsWSFormError
from .service import Service
from .helpers import JSONEncoder, JsonSerializer

from .users.models import User, Role


class UserManipulator(Service):
    __model__ = User

user_manipulator = UserManipulator()

