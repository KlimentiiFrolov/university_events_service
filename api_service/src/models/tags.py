from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin

if TYPE_CHECKING:
    from .event_tags import EventTag

class Tag(Base, IdPrimaryKeyMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)

    events: Mapped[list["EventTag"]] = relationship(back_populates="tag")

    __table_args__ = (
        CheckConstraint('LENGTH(name)>2', name="ck_name_length_gt_2"),
    )
