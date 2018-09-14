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
                               


def upgrade():
        
    
    with op.batch_alter_table('oauth2client') as batch_op:
        batch_op.add_column(sa.Column('ratelimit', sa.Float, default=0.0))
        batch_op.add_column(sa.Column('created', UTCDateTime, default=get_date))
        
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            type_ = sa.types.Float,
            default=2.0)
        batch_op.add_column(sa.Column('_allowed_scopes', sa.Text))
        

def downgrade():
    
    with op.batch_alter_table('oauth2client') as batch_op:
        batch_op.drop_column('ratelimit')
        batch_op.drop_column('created')
        
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            type_ = sa.types.Integer,
            default=2)
        batch_op.drop_column('_allowed_scopes')
