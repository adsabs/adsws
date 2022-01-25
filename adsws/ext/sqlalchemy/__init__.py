from flask_registry import RegistryProxy, ModuleAutoDiscoveryRegistry
from flask_sqlalchemy import SQLAlchemy as FlaskSQLAlchemy

#: Flask-SQLAlchemy extension instance
db = FlaskSQLAlchemy()

models = RegistryProxy('models', ModuleAutoDiscoveryRegistry, 'models')


def setup_app(app):
    """Setup SQLAlchemy extension."""
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite://')
    
    if 'SQLALCHEMY_TRACK_MODIFICATIONS' not in app.config:
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

    ## Let's initialize database.
    db.init_app(app)

    ## pysqlite driver breaks transactions, we have to apply some hacks as per
    ## http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#pysqlite-serializable
    if 'sqlite:' in app.config.get('SQLALCHEMY_DATABASE_URI'):
        from sqlalchemy import event
        engine = db.get_engine(app)
        
        @event.listens_for(engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            # disable pysqlite's emitting of the BEGIN statement entirely.
            # also stops it from emitting COMMIT before any DDL.
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def do_begin(conn):
            # emit our own BEGIN
            conn.execute("BEGIN EXCLUSIVE")


    return app