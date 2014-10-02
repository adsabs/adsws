"""creating default user accounts

Revision ID: 26889be04d70
Revises: 33d84dc97ea1
Create Date: 2014-09-10 00:08:49.335000

"""

# revision identifiers, used by Alembic.
revision = '26889be04d70'
down_revision = '33d84dc97ea1'

from alembic import op
import sqlalchemy as safrom sqlalchemy.sql import table, columnfrom sqlalchemy import String, Integer, Date
from werkzeug.security import gen_saltusers = table('users', column('id', Integer),                  column('name', String),                   column('email', String),                  column('password', String),                  )roles = table('roles', column('id', Integer),                  column('name', String),                   column('description', String))                  permissions = table('permissions', column('id', Integer),                  column('name', String),                   column('description', String))                                    def encrypt_password(password):    from adsws.core.users.models import User    from adsws.factory import create_app    from adsws.core import db         app = create_app('upgrade',                     EXTENSIONS = ['adsws.ext.sqlalchemy',                                   'adsws.ext.security'])    with app.app_context() as c:        u = User(email='foo', password=password)        return u._get_password()
def upgrade():        op.bulk_insert(users,                [                    {'name':'admin', 'email': 'admin@adslabs.org',                     'password': encrypt_password(gen_salt(12))},                    {'name':'anonymous', 'email': 'anonymous@adslabs.org',                     'password': encrypt_password(gen_salt(12))},                ],                multiinsert=False            )            op.bulk_insert(roles,                [                    {'id':1, 'name':'demiurg', 'description': 'can do anything'},                    {'id':2, 'name':'client', 'description': 'can access api'},                ],                multiinsert=True            )            op.bulk_insert(permissions,                [                    {'id':1, 'name':'can_search', 'description': 'can access search'},                    {'id':2, 'name':'can_index', 'description': 'can update index'},                    {'id':3, 'name':'can_create_bigquery', 'description': 'can register semi-persistent query (list of ids)'},                ],                multiinsert=False            )    
    
def downgrade():    op.execute(        users.delete().where(users.c.email==op.inline_literal('admin@adslabs.org'))    )    op.execute(        users.delete().where(users.c.email==op.inline_literal('anonymous@adslabs.org'))    )          
