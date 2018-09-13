"""add User.ratelimit_level

Revision ID: 2e0c0694da22
Revises: 26889be04d70
Create Date: 2015-04-28 17:52:19.553796

"""

# revision identifiers, used by Alembic.
revision = '2e0c0694da22'
down_revision = '26889be04d70'

from alembic import op
import sqlalchemy as sa


def upgrade():

    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('ratelimit_level', sa.Integer))
        

def downgrade():
    
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('ratelimit_level')
