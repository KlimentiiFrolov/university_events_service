from datetime import timedelta

import jwt
import pytest

from src.core.config import settings
from src.core.dates import get_current_datetime
from src.core.tokens import ACCESS_TOKEN_TYPE, create_access_token, decode_access_token
from src.schemas.exceptions.domain import InvalidTokenError

USER_ID = 42


def _encode(
    *,
    secret: str = settings.auth.secret_key,
    algorithm: str = settings.auth.algorithm,
    drop: tuple[str, ...] = (),
    **overrides,
) -> str:
    """Собрать токен вручную: валидный payload, в котором можно заменить или убрать claims."""
    now = get_current_datetime()
    payload = {
        "sub": str(USER_ID),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **overrides,
    }
    for claim in drop:
        payload.pop(claim)

    return jwt.encode(payload, secret, algorithm=algorithm)


def test_decode_returns_user_id_of_created_token():
    assert decode_access_token(create_access_token(USER_ID)) == USER_ID


def test_decode_accepts_manually_built_valid_token():
    assert decode_access_token(_encode()) == USER_ID


def test_decode_rejects_expired_token():
    expired_at = get_current_datetime() - timedelta(seconds=1)

    with pytest.raises(InvalidTokenError, match="expired"):
        decode_access_token(_encode(exp=expired_at))


def test_decode_rejects_token_signed_with_other_secret():
    token = _encode(secret=settings.auth.secret_key + "-other")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_decode_rejects_unsigned_token():
    token = _encode(algorithm="none", secret="")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_decode_rejects_tampered_payload():
    header, payload, signature = create_access_token(USER_ID).split(".")
    forged_payload = _encode(sub="1").split(".")[1]

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{forged_payload}.{signature}")


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c"])
def test_decode_rejects_malformed_token(token: str):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("claim", ["sub", "type", "iat", "exp"])
def test_decode_rejects_token_without_required_claim(claim: str):
    with pytest.raises(InvalidTokenError):
        decode_access_token(_encode(drop=(claim,)))


@pytest.mark.parametrize("token_type", ["refresh", "", "ACCESS"])
def test_decode_rejects_wrong_token_type(token_type: str):
    with pytest.raises(InvalidTokenError, match="type"):
        decode_access_token(_encode(type=token_type))


@pytest.mark.parametrize("sub", ["abc", "", "0", "-1", "1.5"])
def test_decode_rejects_invalid_subject(sub: str):
    with pytest.raises(InvalidTokenError):
        decode_access_token(_encode(sub=sub))


def test_decode_rejects_non_string_subject():
    # По RFC 7519 "sub" — строка; PyJWT отклоняет числовой sub
    with pytest.raises(InvalidTokenError):
        decode_access_token(_encode(sub=USER_ID))
