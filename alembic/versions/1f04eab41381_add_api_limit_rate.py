"""Add api limit rate

Revision ID: 1f04eab41381
Revises: 26889be04d70
Create Date: 2014-10-02 13:28:48.362000

"""

# revision identifiers, used by Alembic.
revision = '1f04eab41381'
down_revision = '26889be04d70'
from alembic import opimport sqlalchemy as sa

def upgrade():
    op.create_table('oauth2client_limits',        sa.Column('client_id', sa.String(length=255), nullable=False, primary_key=True),        sa.Column('counter', sa.Integer, nullable=True, default=0),        sa.Column('expires', sa.DateTime(), nullable=True),        sa.ForeignKeyConstraint(['client_id'], ['oauth2client.client_id'])    )

def downgrade():
    op.drop_table('oauth2client_limits')
