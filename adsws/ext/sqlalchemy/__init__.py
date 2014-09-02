from flask_registry import RegistryProxy, ModuleAutoDiscoveryRegistry
from flask_sqlalchemy import SQLAlchemy as FlaskSQLAlchemy

#: Flask-SQLAlchemy extension instance
db = FlaskSQLAlchemy()

models = RegistryProxy('models', ModuleAutoDiscoveryRegistry, 'models')


def setup_app(app):
    """Setup SQLAlchemy extension."""
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite://')

    ## Let's initialize database.
    db.init_app(app)

    return app