from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy import text as sql_text  # колонка text перекрыла бы эту функцию в теле класса
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Notification(Base):
    """Уведомление конкретному пользователю. delivered_at выставляется по ack клиента."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # created_at заполняет БД; eager_defaults возвращает его сразу в INSERT ... RETURNING,
    # чтобы уведомление можно было отправить клиенту после закрытия сессии
    __mapper_args__= {
        "eager_defaults": True,
    }

    __table_args__ = (
        # При подключении досылаются недоставленные уведомления пользователя
        Index(
            "ix_notifications_undelivered_user_id",
            "user_id",
            postgresql_where=sql_text("delivered_at IS NULL"),
        ),
    )
