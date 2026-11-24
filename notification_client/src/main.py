"""Run with: python -m src.main"""

import asyncio
import logging

from pydantic import ValidationError

from .client import AuthenticationError, run_client
from .core.config import ClientSettings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = ClientSettings()
        asyncio.run(run_client(settings))
    except (AuthenticationError, RuntimeError, ValidationError) as error:
        logging.error("Client stopped: %s", error)
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        logging.info("Notification client stopped")


if __name__ == "__main__":
    main()
