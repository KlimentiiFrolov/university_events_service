from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixins.id_pk_mixin import IdPrimaryKeyMixin


class Tags(Base, IdPrimaryKeyMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)

    __table_args__ = (
        CheckConstraint('LENGTH(name)>2', name="ck_name_length_gt_2"),
    )
