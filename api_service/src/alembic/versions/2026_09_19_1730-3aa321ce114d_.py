"""empty message

Revision ID: 3aa321ce114d
Revises: a535f7860e66, 443c9e207ba7
Create Date: 2026-09-19 17:30:16.563366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3aa321ce114d'
down_revision: Union[str, Sequence[str], None] = ('a535f7860e66', '443c9e207ba7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
