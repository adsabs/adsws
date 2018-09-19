"""Add ratelimit to OAuth clients

Revision ID: 45eb49b7e934
Revises: 2e0c0694da22
Create Date: 2018-09-13 17:27:18.519960

"""

# revision identifiers, used by Alembic.
revision = '45eb49b7e934'
down_revision = '2e0c0694da22'

from alembic import op
import sqlalchemy as sa
from adsmutils import UTCDateTime, get_date

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))                               
from adsws.core import db
from adsws.accounts import create_app
from adsws.modules.oauth2server.models import OAuthToken, OAuthClient
from adsws.core.users import User


def upgrade():
        
    with op.batch_alter_table('oauth2client') as batch_op:
        batch_op.add_column(sa.Column('ratelimit', sa.Float, default=0.0))
        batch_op.add_column(sa.Column('created', UTCDateTime, default=get_date))
        
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            type_ = sa.types.Float)
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            server_default='2.0')
        batch_op.add_column(sa.Column('_allowed_scopes', sa.Text))
        
    # now we are going to migrate data
    # if a user previously had high ratelimit, we will copy it to the oauth client
    
    app = create_app()
    with app.app_context():
        for u in db.session.query(User).filter(User.ratelimit_level >= 2).yield_per(50):
            for c in db.session.query(OAuthClient).filter(OAuthClient.user_id == u.id).all():
                c.ratelimit = u.ratelimit_level
        db.session.commit()
            
            

def downgrade():
    
    with op.batch_alter_table('oauth2client') as batch_op:
        batch_op.drop_column('ratelimit')
        batch_op.drop_column('created')
        
    with op.batch_alter_table('users') as batch_op:
        bbatch_op.alter_column(
            column_name = 'ratelimit_level',
            type_ = sa.types.Integer)
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            server_default='2')
        batch_op.drop_column('_allowed_scopes')
