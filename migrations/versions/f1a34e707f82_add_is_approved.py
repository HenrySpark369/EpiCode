"""Add is_approved

Revision ID: f1a34e707f82
Revises: 965804a43932
Create Date: 2025-06-05 23:02:47.847433

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a34e707f82'
down_revision = '965804a43932'
branch_labels = None
depends_on = None


def upgrade():
    # 1) create users table (with a default for is_approved)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(80), nullable=False, unique=True),
        sa.Column('email', sa.String(120), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(128), nullable=False),
        sa.Column('is_approved', sa.Boolean(), nullable=False,
                  server_default=sa.text('false'))
    )

    # 2) insert a default “system” user (you can change the values here)
    op.execute("""
      INSERT INTO users (id, username, email, password_hash, is_approved)
      VALUES
        (1, 'system', 'system@example.com', 'changeme_hash', true)
    """)
    # if you rely on the sequence, bump it:
    op.execute("SELECT setval(pg_get_serial_sequence('users','id'), max(id)) FROM users")

    # 3) add the new FK‐column as NULLABLE
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    # 4) backfill every row to point at our system user
    op.execute("UPDATE conversations SET user_id = 1 WHERE user_id IS NULL")

    # 5) now make it NOT NULL and add the FK
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              nullable=False)
        batch_op.create_foreign_key('fk_conversations_user',
                                    'users',
                                    ['user_id'], ['id'],
                                    ondelete='CASCADE')

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.drop_constraint('fk_conversations_user', type_='foreignkey')
        batch_op.drop_column('user_id')
    op.drop_table('users')
    # ### end Alembic commands ###
