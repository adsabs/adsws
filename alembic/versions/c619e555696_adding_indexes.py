"""Adding indexes

Revision ID: c619e555696
Revises: 45eb49b7e934
Create Date: 2018-11-05 17:17:08.553335

"""

# revision identifiers, used by Alembic.
revision = 'c619e555696'
down_revision = '45eb49b7e934'

from alembic import op
import sqlalchemy as sa

                               


def upgrade():
    op.create_index('oauth2token_client_id_key', 'oauth2token', ['client_id'])
    op.create_index('oauth2token_user_id_key', 'oauth2token', ['user_id'])
    op.create_index('oauth2token_is_personal_key', 'oauth2token', ['is_personal'])

    op.create_index('oauth2client_user_id_key', 'oauth2client', ['user_id'])
    op.create_index('oauth2client_name_key', 'oauth2client', ['name'])

def downgrade():
    op.drop_index('oauth2token_client_id_key', 'oauth2token')
    op.drop_index('oauth2token_user_id_key', 'oauth2token')
    op.drop_index('oauth2token_is_personal_key', 'oauth2token')

    op.drop_index('oauth2client_user_id_key', 'oauth2client')
    op.drop_index('oauth2client_name_key', 'oauth2client')
