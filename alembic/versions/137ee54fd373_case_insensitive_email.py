"""Case insensitive email

Revision ID: 137ee54fd373
Revises: c619e555696
Create Date: 2021-09-30 17:12:20.572177

"""

# revision identifiers, used by Alembic.
revision = '137ee54fd373'
down_revision = 'c619e555696'

from alembic import op
import sqlalchemy as sa
from adsws.ext.sqlalchemy import db
from citext import CIText


def upgrade():
    #with app.app_context() as c:
    #   db.session.add(Model())
    #   db.session.commit()

    op.alter_column('users', 'email',
                    existing_type=db.String(255),
                    type_=CIText())


def downgrade():
    op.alter_column('users', 'email',
                    existing_type=CIText(),
                    type_=db.String(255))
