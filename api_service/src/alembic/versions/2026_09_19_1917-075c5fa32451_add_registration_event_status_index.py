"""add registration event status index

Revision ID: 075c5fa32451
Revises: dbdb379c0fb3
Create Date: 2026-09-19 19:17:03.001460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '075c5fa32451'
down_revision: Union[str, Sequence[str], None] = 'dbdb379c0fb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_registrations_event_status",
        "registrations",
        ["event_id", "status"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_registrations_event_status",
        table_name="registrations",
    )
