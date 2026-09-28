"""add registration event status index

Revision ID: 4ecd4f38d51c
Revises: 97d3efba835d
Create Date: 2026-09-20 02:20:04.255765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ecd4f38d51c'
down_revision: Union[str, Sequence[str], None] = '97d3efba835d'
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
