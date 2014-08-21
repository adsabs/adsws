from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required

from adsws.core import db, Client, Role

security = Security()    

def setup_app(app):

    user_datastore = SQLAlchemyUserDatastore(db, Client, Role)
    security.init_app(app, user_datastore)

    return app
