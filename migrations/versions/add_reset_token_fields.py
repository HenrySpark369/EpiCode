"""add reset_token fields to users

Revision ID: add_reset_token_fields
Revises: f1a34e707f82
Create Date: 2025-06-15 19:13:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_reset_token_fields'
down_revision = 'f1a34e707f82'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('reset_token', sa.String(length=256), nullable=True))
    op.add_column('users', sa.Column('reset_token_expiration', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'reset_token_expiration')
