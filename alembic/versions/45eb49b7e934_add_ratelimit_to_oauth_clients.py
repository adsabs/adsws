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

 # this is a modified/simplified version of the User and OAuthClient 
 # objects; just to prevent any troubles with changes upstream

users = sa.Table(
    'users',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('email', sa.String(255)),
    sa.Column('ratelimit_level', sa.Integer)
    )
clients = sa.Table(
        'oauth2client',
        sa.MetaData(),
        sa.Column('user_id', sa.Integer),
        sa.Column('client_id', sa.String(255)),
        sa.Column('ratelimit', sa.Float)
    )

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
    connection = op.get_bind()
    
    for user in connection.execute(users.select()):
        if user.email == 'anonymous@ads':
            connection.execute(users.update().where(users.c.id == user.id).values(ratelimit_level=-1.0))
            connection.execute(
                clients.update().where(
                    clients.c.user_id == user.id
                ).values(
                    ratelimit=1.0
                )
            )
        elif user.email and user.email.endswith('@ads'):
            connection.execute(
                clients.update().where(
                    clients.c.user_id == user.id
                ).values(
                    ratelimit=user.ratelimit_level
                )
            )  
        elif user.ratelimit_level and float(user.ratelimit_level) > 1.0:
            # count all the clients (stupid way, dunno how to issue 'count' with alembic)
            print('counting ', user.id)
            i = 0.0
            for c in connection.execute(clients.select().where(clients.c.user_id==user.id)):
                i += 1.0
            print('result', i)
            if i > 0:
                new_limit = float(user.ratelimit_level) / i
                print('updating')
                connection.execute(clients.update().where(
                    clients.c.user_id == user.id
                ).values(
                    ratelimit=new_limit
                ))
        else: # set all others to have ralimit of 1.0
            connection.execute(clients.update().where(
                    clients.c.user_id == user.id
                ).values(
                    ratelimit=1.0
                ))
            
            

def downgrade():
    
    with op.batch_alter_table('oauth2client') as batch_op:
        batch_op.drop_column('ratelimit')
        batch_op.drop_column('created')
        
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            type_ = sa.types.Integer)
        batch_op.alter_column(
            column_name = 'ratelimit_level',
            server_default='2')
        batch_op.drop_column('_allowed_scopes')
