"""Creating basic DB structure

Revision ID: 51f3b3b5cd5d
Revises: None
Create Date: 2014-08-08 20:13:58.241566

"""

# revision identifiers, used by Alembic.
revision = '51f3b3b5cd5d'
down_revision = None

from alembic import op
import sqlalchemy as sa

from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Date
from sqlalchemy_utils import URLType


def upgrade():
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('password', sa.String(length=255), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.Column('current_login_at', sa.DateTime(), nullable=True),
    sa.Column('last_login_ip', sa.String(length=100), nullable=True),
    sa.Column('current_login_ip', sa.String(length=100), nullable=True),
    sa.Column('login_count', sa.Integer(), nullable=True),
    sa.Column('registered_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('roles_users',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint()
    )
    op.create_table('permissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('permissions_users',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('perm_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['perm_id'], ['permissions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint()
    )
    
    

    op.create_table(
        'oauth2client',
        sa.Column('name', sa.String(length=40), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', URLType(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('client_secret', sa.String(length=255), nullable=False),
        sa.Column('is_confidential', sa.Boolean(), nullable=True),
        sa.Column('is_internal', sa.Boolean(), nullable=True),
        sa.Column('_redirect_uris', sa.Text(), nullable=True),
        sa.Column('_default_scopes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint('client_id')
        
    )
    op.create_table(
        'oauth2token',
        sa.Column('id', sa.Integer(), autoincrement=True,
                  nullable=False),
        sa.Column('client_id', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('token_type', sa.String(length=255), nullable=True),
        sa.Column('access_token', sa.String(length=255), nullable=True),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.Column('expires', sa.DateTime(), nullable=True),
        sa.Column('_scopes', sa.Text(), nullable=True),
        sa.Column('is_personal', sa.Boolean(), nullable=True),
        sa.Column('is_internal', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['oauth2client.client_id'], onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('access_token'),
        sa.UniqueConstraint('refresh_token')
    )
    # # Following create index causes problems
    # op.create_index(
    #     'ix_oauth2CLIENT_client_secret', 'oauth2CLIENT', ['client_secret'],
    #     unique=True
    # )

def downgrade():
    op.drop_table('oauth2token')
    op.drop_table('oauth2client')
    
    op.drop_table('permissions_users')
    op.drop_table('permissions')
    op.drop_table('roles_users')
    op.drop_table('roles')

    op.drop_table('users')