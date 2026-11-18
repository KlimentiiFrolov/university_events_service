from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixins.created_at_mixin import CreatedAtMixin


class OutboxMessage(Base, CreatedAtMixin):
    """Сообщение для брокера, записанное в одной транзакции с бизнес-изменением.

    `id` уходит в брокер как `message_id` и служит ключом дедупликации у потребителя.
    """

    __tablename__ = "outbox_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    routing_key: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)

    __table_args__ = (
        # Relay читает только неотправленные сообщения по порядку создания
        Index(
            "ix_outbox_messages_unpublished_created_at",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
    )
