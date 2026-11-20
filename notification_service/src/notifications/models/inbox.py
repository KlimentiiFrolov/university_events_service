from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class InboxMessage(Base):
    """Принятое из RabbitMQ сообщение. По message_id отсекаются повторные доставки."""

    __tablename__ = "inbox_messages"

    message_id: Mapped[UUID] = mapped_column(primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
