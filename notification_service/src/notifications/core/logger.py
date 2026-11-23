import logging

from .config import LoggerSettings, settings


def prepare_logger(name: str, log_config: LoggerSettings) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(level=log_config.level)

    if not log.handlers:  # защита от дублирования handler'а при повторном вызове
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt=log_config.LOG_DEFAULT_FORMAT,
                datefmt=log_config.datefmt,
            )
        )
        log.addHandler(handler)

    log.propagate = False

    return log


log = prepare_logger("notifications", settings.log)
