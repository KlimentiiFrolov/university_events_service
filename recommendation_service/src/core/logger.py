import logging

from src.core.config import LoggerSettings, settings


def prepare_logger(
    name: str,
    config: LoggerSettings,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(config.level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt=config.log_format,
                datefmt=config.datefmt,
            )
        )
        logger.addHandler(handler)

    logger.propagate = False
    return logger


log = prepare_logger("recommendation_service", settings.log)