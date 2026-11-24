"""Authenticate, receive, validate, and display WebSocket notifications."""

import asyncio
import logging
from collections.abc import AsyncIterable, Callable

import httpx
from pydantic import BaseModel, ValidationError
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from .core.config import ClientSettings
from .schemas import NotificationPayload, RecentNotificationIds, format_notification

log = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Credentials / access token were rejected; retrying without a fix won't help."""


class TokenResponse(BaseModel):
    access_token: str


async def obtain_access_token(settings: ClientSettings) -> str:
    """Log in on every reconnect to avoid reusing expired short-lived JWTs."""
    if settings.notification_email and settings.notification_password:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.api_base_url.rstrip('/')}/api/v1/auth/login",
                json={
                    "email": settings.notification_email,
                    "password": settings.notification_password.get_secret_value(),
                },
            )
            if response.status_code in (400, 401, 403, 422):
                raise AuthenticationError("API login rejected the configured credentials")
            response.raise_for_status()
            try:
                return TokenResponse.model_validate(response.json()).access_token
            except (ValidationError, ValueError) as error:
                raise AuthenticationError("API login returned no valid access_token") from error

    if settings.notification_token:
        return settings.notification_token.get_secret_value()
    raise AuthenticationError("Missing login credentials or access token")


async def consume_notifications(
    messages: AsyncIterable[str | bytes],
    seen: RecentNotificationIds,
    *,
    display: Callable[[str], None] = print,
) -> None:
    """Read messages until disconnect; skip malformed JSON and duplicate ids."""
    async for raw in messages:
        try:
            notification = NotificationPayload.model_validate_json(raw)
        except ValidationError as error:
            log.warning("Unexpected WebSocket message, ignored: %s", error)
            continue
        if seen.is_new(notification.id):
            display(format_notification(notification))
        else:
            log.debug("Duplicate notification id=%d suppressed", notification.id)


async def run_client(settings: ClientSettings) -> None:
    """Reconnect after temporary failures; renew access token on every attempt."""
    seen = RecentNotificationIds()
    delay = settings.reconnect_initial_seconds

    while True:
        try:
            token = await obtain_access_token(settings)
            async with connect(
                settings.notification_ws_url,
                additional_headers={"Authorization": f"Bearer {token}"},
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20,
            ) as websocket:
                log.info("Connected to %s", settings.notification_ws_url)
                delay = settings.reconnect_initial_seconds
                await consume_notifications(websocket, seen)
                log.info("WebSocket closed normally")
        except InvalidStatus as error:
            if error.response.status_code in (401, 403):
                raise AuthenticationError(
                    "WebSocket authentication rejected; check JWT / credentials"
                ) from error
            if error.response.status_code == 404:
                raise RuntimeError("WebSocket endpoint not found; check NOTIFICATION_WS_URL") from error
            log.warning("WebSocket handshake failed: HTTP %s", error.response.status_code)
        except (ConnectionClosed, OSError, TimeoutError, httpx.HTTPError) as error:
            log.warning("Connection unavailable: %s", error)

        log.info("Reconnecting in %.1f seconds", delay)
        await asyncio.sleep(delay)
        delay = min(delay * 2, settings.reconnect_max_seconds)
