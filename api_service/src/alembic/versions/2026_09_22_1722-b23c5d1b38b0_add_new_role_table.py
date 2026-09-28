"""add new role table

Revision ID: b23c5d1b38b0
Revises: b3e2f6c7a814
Create Date: 2026-09-22 17:22:55.699298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b23c5d1b38b0'
down_revision: Union[str, Sequence[str], None] = 'b3e2f6c7a814'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'roles',
        sa.Column(
            'name',
            sa.Enum('participant', 'organizer', name='role_name', native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.execute(
        """
        INSERT INTO roles (name)
        VALUES ('participant'), ('organizer')
        """
    )

    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE users
        SET role_id = roles.id
        FROM roles
        WHERE roles.name = users.role
        """
    )

    op.alter_column('users', 'role_id', nullable=False)

    op.create_foreign_key(
        'fk_users_role_id_roles',
        'users',
        'roles',
        ['role_id'],
        ['id'],
    )

    op.drop_column('users', 'role')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'users',
        sa.Column(
            'role',
            sa.VARCHAR(length=32),
            server_default=sa.text("'participant'::character varying"),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE users
        SET role = roles.name
        FROM roles
        WHERE roles.id = users.role_id
        """
    )

    op.alter_column('users', 'role', nullable=False)

    op.create_check_constraint(
        'ck_users_role',
        'users',
        "role IN ('participant', 'organizer')",
    )

    op.drop_constraint('fk_users_role_id_roles', 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')
    op.drop_table('roles')
