from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin

if TYPE_CHECKING:
    from .events import Event
    from .users import User


class Registration(Base, IdPrimaryKeyMixin):
    __tablename__ = "registrations"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="active",
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="registrations",
    )

    event: Mapped["Event"] = relationship(
        back_populates="registrations",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_registrations_user_event",
        ),
        CheckConstraint(
            "status IN ('active', 'cancelled')",
            name="ck_registrations_status",
        ),
    )