"""WebSocket-эндпоинт уведомлений: /ws/notifications, заголовок Authorization: Bearer <token>."""

from collections.abc import Callable
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
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

from .delivery import push_undelivered
from .manager import ConnectionManager


def build_router(
    manager: ConnectionManager,
    auth: AuthSettings,
    *,
    session_factory: Callable[[], AsyncSession] = async_session_maker,
) -> APIRouter:
    router = APIRouter()

    async def get_current_user_id(
        authorization: Annotated[str | None, Header()] = None,
    ) -> int:
        """id пользователя из заголовка Authorization: Bearer <access token>, как в api_service.

        Нет заголовка, не та схема или невалидный токен - закрытие с кодом 1008.
        """
        try:
            scheme, _, token = (authorization or "").partition(" ")
            if scheme.lower() != "bearer" or not token:
                raise InvalidTokenError("Missing bearer token")

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
            await push_undelivered(manager, user_id, session_factory)

            # Клиент ничего не присылает; чтение нужно, чтобы заметить отключение
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(user_id, websocket)

    return router
