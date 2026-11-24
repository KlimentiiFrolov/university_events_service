import pytest
from pydantic import SecretStr, ValidationError

from src.core.config import ClientSettings


def test_no_credentials_is_rejected():
    with pytest.raises(ValidationError, match="Configure NOTIFICATION_EMAIL"):
        ClientSettings(
            notification_email=None,
            notification_password=None,
            notification_token=None,
        )


def test_invalid_ws_endpoint_is_rejected():
    with pytest.raises(ValidationError, match="NOTIFICATION_WS_URL"):
        ClientSettings(notification_ws_url="http://localhost:8001/ws", notification_token=SecretStr("jwt"))


def test_password_without_email_is_rejected():
    with pytest.raises(ValidationError, match="Set both"):
        ClientSettings(notification_email=None, notification_password=SecretStr("pw"), notification_token=SecretStr("jwt"))
