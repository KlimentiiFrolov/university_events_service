from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin

if TYPE_CHECKING:
    from .events import Event
    from .registrations import Registration
    from .roles import Role


class User(Base, IdPrimaryKeyMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
    )

    second_name: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False,
    )

    role: Mapped["Role"] = relationship(
        back_populates="users",
        lazy="joined",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.second_name}".strip()

    created_events: Mapped[list["Event"]] = relationship(
        back_populates="created_by"
    )

    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )