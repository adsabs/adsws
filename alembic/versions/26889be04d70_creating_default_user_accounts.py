"""creating default user accounts

Revision ID: 26889be04d70
Revises: 33d84dc97ea1
Create Date: 2014-09-10 00:08:49.335000

"""

# revision identifiers, used by Alembic.
revision = '26889be04d70'
down_revision = '33d84dc97ea1'

from alembic import op
import sqlalchemy as safrom sqlalchemy.sql import table, column
from werkzeug.security import gen_saltfrom adsws.core.users.models import User
from adsws.factory import create_appfrom adsws.core import db app = create_app('upgrade',                 EXTENSIONS = ['adsws.ext.sqlalchemy',                               'adsws.ext.security'])
def upgrade():    with app.app_context() as c:        u = User(id=-1, name='Anonymous',                 login='anonymous@adslabs.org',                 email='anonymous@adslabs.org',                  password=gen_salt(12))        db.session.add(u)        db.session.commit()    
    
def downgrade():    with app.app_context() as c:
        anonymous = User.query.get(-1)        if anonymous:            db.session.delete(anonymous)            db.session.commit()
