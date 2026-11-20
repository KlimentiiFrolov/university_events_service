"""create outbox_messages

Revision ID: 5c0a7e3f9b21
Revises: d1f8d0e9bdf2
Create Date: 2026-11-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5c0a7e3f9b21'
down_revision: Union[str, Sequence[str], None] = 'd1f8d0e9bdf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'outbox_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('routing_key', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_outbox_messages_unpublished_created_at',
        'outbox_messages',
        ['created_at'],
        unique=False,
        postgresql_where=sa.text('published_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_outbox_messages_unpublished_created_at',
        table_name='outbox_messages',
        postgresql_where=sa.text('published_at IS NULL'),
    )
    op.drop_table('outbox_messages')
