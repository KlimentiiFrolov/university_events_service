"""Environment-driven settings for the standalone notification client."""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[2]


class ClientSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(SERVICE_DIR / ".env.template", SERVICE_DIR / ".env"),
        extra="ignore",
    )

    notification_ws_url: str = "ws://notification_service:8001/ws/notifications"
    api_base_url: str = "http://api_service:8000"
    notification_email: str | None = None
    notification_password: SecretStr | None = None
    notification_token: SecretStr | None = None
    reconnect_initial_seconds: Annotated[float, Field(gt=0)] = 1.0
    reconnect_max_seconds: Annotated[float, Field(gt=0)] = 30.0

    @model_validator(mode="after")
    def validate_settings(self) -> "ClientSettings":
        parsed = urlsplit(self.notification_ws_url)
        if parsed.scheme not in ("ws", "wss") or not parsed.hostname:
            raise ValueError("NOTIFICATION_WS_URL must be a valid ws:// or wss:// URL")
        api = urlsplit(self.api_base_url)
        if api.scheme not in ("http", "https") or not api.hostname:
            raise ValueError("API_BASE_URL must be a valid http:// or https:// URL")
        if self.reconnect_max_seconds < self.reconnect_initial_seconds:
            raise ValueError("RECONNECT_MAX_SECONDS must be >= RECONNECT_INITIAL_SECONDS")
        if bool(self.notification_email) != bool(self.notification_password):
            raise ValueError("Set both NOTIFICATION_EMAIL and NOTIFICATION_PASSWORD")
        # When no credentials are configured, main.py prompts for them in a terminal.
        # Docker/non-interactive runs must still supply credentials via the environment.
        return self
