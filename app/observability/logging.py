import logging
import sys


LOGGER_NAME = "asyncapi"


def configure_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s "
        "request_id=%(request_id)s "
        "logger=%(name)s "
        "message=%(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def get_logger(name: str) -> logging.LoggerAdapter:
    logger = logging.getLogger(f"{LOGGER_NAME}.{name}")

    return logging.LoggerAdapter(
        logger,
        {"request_id": "-"},
    )
