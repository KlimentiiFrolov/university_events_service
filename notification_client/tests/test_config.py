import pytest
from pydantic import SecretStr, ValidationError

from src.client import AuthenticationError
from src.core.config import ClientSettings
from src.main import resolve_credentials


def test_no_credentials_allow_interactive_login():
    settings = ClientSettings(
        notification_email=None,
        notification_password=None,
        notification_token=None,
    )
    assert settings.notification_email is None
    assert settings.notification_password is None


def test_interactive_credentials_are_used_without_editing_env():
    settings = ClientSettings(
        notification_email=None,
        notification_password=None,
        notification_token=None,
    )
    updated = resolve_credentials(
        settings,
        credentials_provider=lambda: ("organizer@example.com", "password"),
    )
    assert updated.notification_email == "organizer@example.com"
    assert updated.notification_password.get_secret_value() == "password"
    assert settings.notification_email is None  # original settings unchanged


def test_configured_credentials_do_not_trigger_prompt():
    settings = ClientSettings(
        notification_email="organizer@example.com",
        notification_password=SecretStr("password"),
        notification_token=None,
    )

    def unexpected_prompt():
        raise AssertionError("Prompt should not be called")

    assert resolve_credentials(settings, credentials_provider=unexpected_prompt) is settings


def test_empty_prompt_credentials_are_rejected():
    settings = ClientSettings(
        notification_email=None,
        notification_password=None,
        notification_token=None,
    )
    with pytest.raises(AuthenticationError, match="must not be empty"):
        resolve_credentials(settings, credentials_provider=lambda: ("", ""))


def test_invalid_ws_endpoint_is_rejected():
    with pytest.raises(ValidationError, match="NOTIFICATION_WS_URL"):
        ClientSettings(
            notification_ws_url="http://localhost:8001/ws",
            notification_token=SecretStr("jwt"),
        )


def test_invalid_ticket_endpoint_is_rejected():
    with pytest.raises(ValidationError, match="NOTIFICATION_TICKET_URL"):
        ClientSettings(
            notification_ticket_url="ws://localhost:8001/ws/tickets",
            notification_token=SecretStr("jwt"),
        )


def test_password_without_email_is_rejected():
    with pytest.raises(ValidationError, match="Set both"):
        ClientSettings(
            notification_email=None,
            notification_password=SecretStr("pw"),
            notification_token=SecretStr("jwt"),
        )
