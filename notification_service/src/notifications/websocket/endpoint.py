"""WebSocket-эндпоинт уведомлений: /ws/notifications?token=<access token>."""

from collections.abc import Callable
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.core.config import AuthSettings
from notifications.core.database import async_session_maker
from notifications.core.logger import log
from notifications.core.tokens import InvalidTokenError, decode_access_token
from notifications.repositories.notifications import NotificationRepository
from notifications.schemas.websocket import NotificationPayload

from .manager import ConnectionManager


async def send_undelivered(
    websocket: WebSocket,
    user_id: int,
    session_factory: Callable[[], AsyncSession],
) -> None:
    """Дослать уведомления, которые пользователь ещё не получил, и отметить их доставленными.

    Если соединение оборвётся посреди досылки, транзакция откатится и при следующем
    подключении всё придёт снова (уже полученное - повторно).
    """
    async with session_factory() as session, session.begin():
        repository = NotificationRepository(session)
        notifications = await repository.list_undelivered(user_id)

        for notification in notifications:
            payload = NotificationPayload.from_model(notification).model_dump(mode="json")
            await websocket.send_json(payload)

        await repository.mark_delivered([notification.id for notification in notifications])

    if notifications:
        log.info("Sent %d undelivered notification(s) to user id=%d", len(notifications), user_id)


def build_router(
    manager: ConnectionManager,
    auth: AuthSettings,
    *,
    session_factory: Callable[[], AsyncSession] = async_session_maker,
) -> APIRouter:
    router = APIRouter()

    async def get_current_user_id(token: Annotated[str, Query()] = "") -> int:
        """id пользователя из access-токена. Токен в query: браузерный WebSocket
        не умеет передавать заголовки. Невалидный токен - закрытие с кодом 1008."""
        try:
            return decode_access_token(token, auth)
        except InvalidTokenError as error:
            log.warning("WebSocket connection rejected: %s", error)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from error

    @router.websocket("/ws/notifications")
    async def notifications_websocket(
        websocket: WebSocket,
        user_id: Annotated[int, Depends(get_current_user_id)],
    ) -> None:
        await websocket.accept()
        # Регистрируемся до досылки: новое уведомление, сохранённое во время досылки,
        # не потеряется (в худшем случае придёт дважды - клиент отличает по id)
        manager.connect(user_id, websocket)
        try:
            await send_undelivered(websocket, user_id, session_factory)
            # Клиент ничего не присылает; чтение нужно, чтобы заметить отключение
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(user_id, websocket)

    return router
