"""Зависимости FastAPI: настройки, общее состояние процесса и авторизация.

Состояние (реестр подключений, тикеты, фабрика сессий) кладёт в app.state
NotificationLifespan.bind(); HTTPConnection подходит и для HTTP, и для WebSocket.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, WebSocketException, status
from fastapi.requests import HTTPConnection
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.core.config import settings
from notifications.core.logger import log
from notifications.core.tokens import InvalidTokenError, decode_access_token
from notifications.lifespan import NotificationLifespan
from notifications.websocket.manager import ConnectionManager
from notifications.websocket.tickets import TicketStore


def get_notification_lifespan(connection: HTTPConnection) -> NotificationLifespan:
    return connection.app.state.notifications


NotificationLifespanDep = Annotated[NotificationLifespan, Depends(get_notification_lifespan)]


def get_connection_manager(lifespan: NotificationLifespanDep) -> ConnectionManager:
    return lifespan.manager


def get_ticket_store(lifespan: NotificationLifespanDep) -> TicketStore:
    return lifespan.tickets


def get_session_factory(lifespan: NotificationLifespanDep) -> Callable[[], AsyncSession]:
    return lifespan.session_factory


ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]
TicketStoreDep = Annotated[TicketStore, Depends(get_ticket_store)]
SessionFactoryDep = Annotated[Callable[[], AsyncSession], Depends(get_session_factory)]


# HTTP: access-токен api_service
# auto_error=False: отсутствие заголовка обрабатываем сами, как в api_service
bearer_scheme = HTTPBearer(auto_error=False)

def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    """id пользователя из заголовка Authorization: Bearer <access token>."""
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        return decode_access_token(credentials.credentials, settings.auth)
    except InvalidTokenError as error:
        # Причину пишем только в лог: клиенту подробности проверки токена не нужны
        log.warning("Access token rejected: %s", error)
        raise _unauthorized("Invalid token") from error


CurrentUserIdDep = Annotated[int, Depends(get_current_user_id)]


# WebSocket: одноразовый тикет
def get_ws_user_id(
    tickets: TicketStoreDep,
    authorization: Annotated[str | None, Header()] = None,
    ticket: Annotated[str | None, Query()] = None,
) -> int:
    """id пользователя по тикету из POST /ws/tickets; тикет при этом гасится.

    Тикет передаётся в заголовке Authorization: Bearer <ticket> (Python-клиент, Postman)
    или в ?ticket=<ticket> (браузер не умеет ставить заголовки). Если есть заголовок,
    query не смотрим. Access-токен вместо тикета не принимается.

    Нет тикета, не та схема, тикет неизвестен, истёк или уже использован - закрытие с кодом 1008.
    """
    value = ticket
    if authorization is not None:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() != "bearer":
            value = None

    user_id = tickets.consume(value) if value else None
    if user_id is None:
        log.warning("WebSocket connection rejected: missing or invalid ticket")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    return user_id


WsUserIdDep = Annotated[int, Depends(get_ws_user_id)]
