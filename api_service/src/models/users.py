from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin

if TYPE_CHECKING:
    from .events import Event

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

    events: Mapped[list["Event"]] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint(
            "role IN ('participant', 'organizer')",
            name="ck_users_role",
        ),
    )