# -*- coding: utf-8 -*-
"""
    adsws.services
    ~~~~~~~~~~~~~~~~~

    services module: these objects are there available to every instance of the 
    AdsWS application
"""

from .users import UsersService

#: An instance of the :class:`UsersService` class
users = UsersService()
