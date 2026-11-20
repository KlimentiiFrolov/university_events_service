"""Проверка access-токенов, выданных api_service (те же JWT_SECRET и JWT_ALGORITHM)."""

import jwt

from notifications.core.config import AuthSettings

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str, auth: AuthSettings) -> int:
    """Проверить токен доступа и вернуть id пользователя из claim "sub".

    Raises:
        InvalidTokenError: неверная подпись или формат, истёк срок действия,
            нет обязательных claims, тип не "access" или "sub" не id пользователя.
    """
    try:
        payload = jwt.decode(
            token,
            auth.secret_key,
            algorithms=[auth.algorithm],
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
