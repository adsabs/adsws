from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required


security = Security()    

def setup_app(app):
    from adsws.core import db, Client, Role
    user_datastore = SQLAlchemyUserDatastore(db, Client, Role)
    security.init_app(app, user_datastore)

    return app
