========================
ADSWS - ADS Web Services
========================

.. image:: https://travis-ci.org/adsabs/adsws.png?branch=master
    :target: https://travis-ci.org/adsabs/adsws
.. image:: https://coveralls.io/repos/adsabs/adsws/badge.png?branch=master
    :target: https://coveralls.io/r/adsabs/adsws


About
=====
ADSWS is a set of tools to expose (any) web services - both internal and
external - inside/outside of ADS.

Installation
============

    git clone https://github.com/adsabs/adsws.git
    cd adsws
    virtualenv python
    pip install -r requirements.txt 
    pip install -r dev-requirements.txt
    alembic upgrade head
    vim instance/local_config.py # edit edit edit...
    python wsgi.py
        


Testing
=======
Running the test suite is as simple as: ::

    ./run-tests.sh