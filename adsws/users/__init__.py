# -*- coding: utf-8 -*-
"""
    adsws.users
    ~~~~~~~~~~~~~~

    adsws users package
"""

from ..core import Service
from .models import User


class UsersService(Service):
    __model__ = User
