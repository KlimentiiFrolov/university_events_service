"""Run with: python -m src.main"""

import asyncio
import getpass
import logging
import sys
from collections.abc import Callable

from pydantic import SecretStr, ValidationError

from .client import AuthenticationError, run_client
from .core.config import ClientSettings


def prompt_for_credentials() -> tuple[str, str]:
    """Ask for credentials on a terminal; never echo the password."""
    if not sys.stdin.isatty():
        raise AuthenticationError(
            "No credentials configured. Set NOTIFICATION_EMAIL and "
            "NOTIFICATION_PASSWORD (or NOTIFICATION_TOKEN) for non-interactive runs."
        )
    try:
        return input("Email: ").strip(), getpass.getpass("Password: ")
    except EOFError as error:
        raise AuthenticationError("Credentials were not provided") from error


def resolve_credentials(
    settings: ClientSettings,
    *,
    credentials_provider: Callable[[], tuple[str, str]] = prompt_for_credentials,
) -> ClientSettings:
    """Use configured credentials, or request them without editing .env."""
    if settings.notification_token or (
        settings.notification_email and settings.notification_password
    ):
        return settings

    email, password = credentials_provider()
    if not email or not password:
        raise AuthenticationError("Email and password must not be empty")

    # Revalidate the full settings model with the supplied values.
    return ClientSettings(
        **{
            **settings.model_dump(),
            "notification_email": email,
            "notification_password": SecretStr(password),
        }
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = resolve_credentials(ClientSettings())
        asyncio.run(run_client(settings))
    except (AuthenticationError, RuntimeError, ValidationError) as error:
        logging.error("Client stopped: %s", error)
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        logging.info("Notification client stopped")


if __name__ == "__main__":
    main()
