import logging
import sys

import structlog

from app.config import settings
from app.log_redaction import (
    RedactingLogFilter,
    RecursiveLogRedactor,
    is_sensitive_key,
)

_configured = False


def _configured_secret_literals() -> list[str]:
    return [
        value
        for name, value in settings.model_dump().items()
        if is_sensitive_key(name) and isinstance(value, str)
    ]


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    redactor = RecursiveLogRedactor(secret_literals=_configured_secret_literals())
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
        structlog.processors.format_exc_info,
        redactor,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactingLogFilter(redactor))
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(),
            ],
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.disabled = False

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    _configured = True


def get_logger(name: str):
    return structlog.get_logger(name)
