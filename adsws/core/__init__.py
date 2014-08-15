# -*- coding: utf-8 -*-
"""
    adsws.core
    ~~~~~~~~~~~~~

    core module: loaded by every app that runs in ADSWS container
"""


from ..ext.security import security
from ..ext.mail import mail
from ..ext.sqlalchemy import db

from .errors import *
from .service import Service
from .helpers import JSONEncoder, JsonSerializer

from .clients.models import Client


class ClientManipulator(Service):
    __model__ = Client

client_manipulator = ClientManipulator()

