The service is deployed as api.somewhere.org

The service, albeit accessible under one URL, is made of
several _separate_ wsgi applications. These applications
do not have access to each other. Each of them has access
to the same database though.

But you will not be aware of it when you access the URL,
the `wsgi.py` is where you need to look.


Currently, these are the urls:

	/ (root: `adsws.frontend`)
		login
		logout
		register
		info
	/v1 (api: `adsws.api`)
		/search
		/qtree
		/bumblebee/bootstrap


Each of the mini-applications loads configuration:

	# `adsws/config.py` (this is global)
	# `adsws/<mini-app-name>/config.py`
	# `adsws/instance/local_config.py`


TODO: fix alembic and application loading

The paths are relative to the application root, ie.
`adsws/adsws`


Configuration:
==============

Each mini application is made of several other modules,
packages and views. They are configured in the mini-app
config. These components will be loaded when the mini-app
is instantiated (through the call to factory.create_app())

see: http://flask.pocoo.org/docs/0.10/patterns/appdispatch/

_It is important that you understand this lego principle._

Example of `adsws.api.config`:

```
EXTENSIONS = ['adsws.ext.menu',
              'adsws.ext.sqlalchemy',
              'adsws.ext.security',]

PACKAGES = ['adsws.modules.oauth2server',
            'adsws.api.solr',
            'adsws.api.bumblebee']
```            


Access to the resources under '/' is governed by 
standard cookies-session mechanism.

Users need to login (authenticate), server gives
them a cookie and at the same time the session is
persisted in a database. Each mini-app has access
to the database and can understand whether the
cookie belongs to the same user, however only the
`frontend` should be changing the data (in other
words: all other mini-apps work in read-only mode)

Access to resources under '/v1' requires OAUTH2
token. 


