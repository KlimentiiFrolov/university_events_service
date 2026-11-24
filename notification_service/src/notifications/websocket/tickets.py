"""Одноразовые короткоживущие тикеты для подключения к WebSocket.

Браузерный WebSocket не умеет передавать заголовки, поэтому вместо access-токена клиент
получает по HTTP тикет и передаёт его при подключении. Тикет одноразовый и быстро истекает,
так что его попадание в логи (например, в query-строке) не страшно.

Тикеты живут в памяти процесса: выдаёт и гасит их один и тот же процесс, как и
ConnectionManager, поэтому сервис рассчитан на один экземпляр. После рестарта тикеты
пропадают - клиент просто запросит новый.
"""

import secrets
import time
from collections.abc import Callable


# сделано пока в in-memory, чтобы не переусложнять и не добавлять новый контейнер для Redis ради одной функции
# понятное дело, что есть трейдоффы в виде того, что у нескольких инстансов свое хранилище и что при перезапуске пропадут токены
class TicketStore:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        # Монотонные часы: перевод системного времени не продлевает и не обрывает тикеты
        self._clock = clock
        # тикет -> (id пользователя, момент истечения)
        self._tickets: dict[str, tuple[int, float]] = {}

    def issue(self, user_id: int, ttl_seconds: float) -> str:
        """Выдать новый тикет пользователю."""
        now = self._clock()
        # Ленивая чистка: невостребованные тикеты не копятся без фоновой задачи
        self._purge_expired(now)

        ticket = secrets.token_urlsafe(32)
        self._tickets[ticket] = (user_id, now + ttl_seconds)
        return ticket

    def consume(self, ticket: str) -> int | None:
        """Погасить тикет и вернуть id пользователя; None - тикета нет, он истёк или уже использован."""
        # pop без await между проверкой и удалением: в asyncio два подключения
        # не смогут использовать один тикет
        entry = self._tickets.pop(ticket, None)
        if entry is None:
            return None

        user_id, expires_at = entry
        if self._clock() >= expires_at:
            return None

        return user_id

    def __len__(self) -> int:
        return len(self._tickets)

    def _purge_expired(self, now: float) -> None:
        expired = [ticket for ticket, (_, expires_at) in self._tickets.items() if expires_at <= now]
        for ticket in expired:
            del self._tickets[ticket]
