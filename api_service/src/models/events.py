from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.created_at_mixin import CreatedAtMixin
from .mixins.id_pk_mixin import IdPrimaryKeyMixin

if TYPE_CHECKING:
    from .event_tags import EventTag
    from .users import User


class Event(Base, IdPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "events"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    text: Mapped[str] = mapped_column(Text(), nullable=True)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    event_date: Mapped[str] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int] = mapped_column(nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    event_tags: Mapped[list["EventTag"]] = relationship(back_populates="event")

    created_by: Mapped["User"] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_capacity_ge_0"),
    ) 

    
