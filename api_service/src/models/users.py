from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin


class User(Base, IdPrimaryKeyMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="participant",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('participant', 'organizer')",
            name="ck_users_role",
        ),
    )