
ADSWS - ADS Web Services
========================

[![Travis Status](https://travis-ci.org/adsabs/adsws.png?branch=master)](https://travis-ci.org/adsabs/adsws)

[![Coverage Status](https://img.shields.io/coveralls/adsabs/adsws.svg)](https://coveralls.io/r/adsabs/adsws)



About
=====
ADSWS is a set of tools to expose (any) web services - both internal and
external - inside/outside of ADS.

Installation
============

```
    git clone https://github.com/adsabs/adsws.git
    cd adsws
    virtualenv python
    pip install -r requirements.txt 
    pip install -r dev-requirements.txt
    alembic upgrade head
    vim instance/local_config.py # edit edit edit...
    python wsgi.py
```        

In case you wondered: the secret keys committed into this repository are used
only for development.


Testing
=======
Running the test suite:

    ./run-tests.sh

or alternatively:

    py.test adsws
