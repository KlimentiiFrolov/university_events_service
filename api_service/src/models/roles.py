from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin

if TYPE_CHECKING:
    from .users import User


class RoleName(StrEnum):
    PARTICIPANT = "participant"
    ORGANIZER = "organizer"


class Role(Base, IdPrimaryKeyMixin):
    __tablename__ = "roles"

    name: Mapped[RoleName] = mapped_column(
        Enum(
            RoleName,
            name="role_name",
            native_enum=False,
            length=32,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        unique=True,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="role",
    )
