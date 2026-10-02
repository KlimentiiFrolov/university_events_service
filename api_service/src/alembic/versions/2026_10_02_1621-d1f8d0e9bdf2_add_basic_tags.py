"""add basic tags

Revision ID: d1f8d0e9bdf2
Revises: 80f2e8f26d1e
Create Date: 2026-10-02 16:21:21.141928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


# revision identifiers, used by Alembic.
revision: str = 'd1f8d0e9bdf2'
down_revision: Union[str, Sequence[str], None] = '80f2e8f26d1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BASIC_TAGS = (
    "IT",
    "Science",
    "Career",
    "Education",
    "Sport",
    "Culture",
    "Art",
    "Volunteering",
    "Hackathon",
    "Networking",
)

# Снимок таблицы на момент миграции, а не модель Tag: миграция не должна
# зависеть от того, как модель изменится в будущем
tags_table = sa.table(
    'tags',
    sa.column('id', sa.Integer()),
    sa.column('name', sa.String()),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        insert(tags_table)
        .values([{"name": name} for name in BASIC_TAGS])
        .on_conflict_do_nothing(index_elements=["name"])
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        tags_table.delete().where(tags_table.c.name.in_(BASIC_TAGS))
    )
