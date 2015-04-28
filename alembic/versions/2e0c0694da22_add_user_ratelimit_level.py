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
    #with app.app_context() as c:
    #   db.session.add(Model())
    #   db.session.commit()
    op.add_column('users', sa.Column('ratelimit_level', sa.Integer))


def downgrade():
    op.drop_column('users', 'ratelimit_level')
