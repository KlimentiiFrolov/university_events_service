"""Access-токены как у api_service - для тестов авторизации.

Подписываются тем же settings.auth, которым их проверяет сервис.
"""

from datetime import UTC, datetime, timedelta

import jwt

from src.notifications.core.config import settings

AUTH = settings.auth
USER_ID = 7


def make_token(
    user_id: int = USER_ID,
    *,
    token_type: str = "access",
    expires_in: timedelta = timedelta(minutes=5),
    secret: str = AUTH.secret_key,
) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, secret, algorithm=AUTH.algorithm)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
