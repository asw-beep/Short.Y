"""Structured logging (Phase 2).

structlog rendered as JSON (prod) or a colourised console (dev), with stdlib and
uvicorn logs routed through the *same* formatter so everything is one consistent
stream. A per-request `request_id` is bound via contextvars, so every log line
emitted while handling a request carries it automatically — no manual plumbing.
"""
import logging
import sys

import structlog

from app.core.config import settings

# Processors shared by structlog-native and stdlib (foreign) log records, so a
# uvicorn log and an app log come out with the same shape.
_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
]


def configure_logging() -> None:
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # Let uvicorn's own loggers flow through our root handler instead of their
    # default formatting; disable the duplicate access log (we log requests
    # ourselves in the middleware, with request_id + duration).
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False


def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
