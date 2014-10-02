"""persistent session storage in database

Revision ID: 33d84dc97ea1
Revises: 51f3b3b5cd5d
Create Date: 2014-09-09 11:30:32.615000

"""

# revision identifiers, used by Alembic.
revision = '33d84dc97ea1'
down_revision = '51f3b3b5cd5d'

from alembic import op
import sqlalchemy as db


def upgrade():
    op.create_table('session',        db.Column('session_key', db.String(36), nullable=False,                            server_default='', primary_key=True),        db.Column('session_expiry', db.DateTime, nullable=True, index=True),        db.Column('session_object', db.LargeBinary, nullable=True),        db.Column('uid', db.Integer(), nullable=False, index=True)    )

def downgrade():
    op.drop_table('session')
