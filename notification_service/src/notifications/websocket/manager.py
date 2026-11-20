"""Реестр WebSocket-подключений пользователей.

Подключения живут в памяти процесса, поэтому сервис рассчитан на один экземпляр.
"""

from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from notifications.core.logger import log


class ConnectionManager:
    def __init__(self) -> None:
        # У пользователя может быть несколько подключений: вкладки, устройства
        self._connections: defaultdict[int, set[WebSocket]] = defaultdict(set)

    def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Зарегистрировать уже принятое (accept) подключение."""
        self._connections[user_id].add(websocket)
        log.info("User id=%d connected, %d connection(s)", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if connections is None:
            return

        connections.discard(websocket)
        if not connections:
            del self._connections[user_id]
        log.info("User id=%d disconnected", user_id)

    def is_connected(self, user_id: int) -> bool:
        return user_id in self._connections

    async def send_to_user(self, user_id: int, payload: dict[str, Any]) -> int:
        """Отправить сообщение во все подключения пользователя и вернуть число успешных.

        Подключение, в которое не удалось отправить, считается мёртвым и удаляется.
        """
        delivered = 0
        # Копия: disconnect меняет набор во время обхода
        for websocket in list(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:  # noqa: BLE001 - клиент мог отключиться не попрощавшись
                log.warning("Sending to user id=%d failed, connection dropped", user_id)
                self.disconnect(user_id, websocket)
            else:
                delivered += 1

        return delivered
