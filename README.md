
ADSWS - ADS Web Services
========================

[![Travis Status](https://travis-ci.org/adsabs/adsws.png?branch=master)](https://travis-ci.org/adsabs/adsws)
[![Coverage Status](https://img.shields.io/coveralls/adsabs/adsws.svg)](https://coveralls.io/r/adsabs/adsws)



About
=====
Core API module for the NASA-ADS, handling:
 - authentication
 - passing requests to the correct local and/or remote microservices
 - rate limiting


Installation
============

```
    git clone https://github.com/adsabs/adsws.git
    pip install -r requirements.txt 
    alembic upgrade head
    vim instance/local_config.py # edit edit edit...
    python wsgi.py
```        

Testing
=======

```
    pip install -r dev-requirements.txt
    py.test adsws
```
