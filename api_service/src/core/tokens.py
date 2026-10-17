from datetime import timedelta

import jwt

from src.core.config import settings
from src.core.dates import get_current_datetime
from src.schemas.exceptions.domain import InvalidTokenError

ACCESS_TOKEN_TYPE = "access"


def create_access_token(
    user_id: int,
) -> str:
    now = get_current_datetime()

    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(
            minutes=(
                settings.auth
                .access_token_expire_minutes
            )
        ),
    }

    return jwt.encode(
        payload,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )


def decode_access_token(
    token: str,
) -> int:
    """Проверить токен доступа и вернуть id пользователя из claim "sub".

    Raises:
        InvalidTokenError: неверная подпись или формат, истёк срок действия,
            нет обязательных claims, тип не "access" или "sub" не id пользователя.
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise InvalidTokenError("Token has expired") from error
    except jwt.InvalidTokenError as error:
        raise InvalidTokenError(f"Invalid token: {error}") from error

    if payload["type"] != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError(f"Invalid token type: {payload['type']}")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as error:
        raise InvalidTokenError("Invalid token subject") from error

    if user_id <= 0:
        raise InvalidTokenError("Invalid token subject")

    return user_id
