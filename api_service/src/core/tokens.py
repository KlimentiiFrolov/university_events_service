from datetime import timedelta

import jwt

from src.core.config import settings
from src.core.dates import get_current_datetime


def create_access_token(
    user_id: int,
) -> str:
    now = get_current_datetime()

    payload = {
        "sub": str(user_id),
        "type": "access",
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