"""Structured JSON logging with secret redaction (structlog events AND stdlib loggers)."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

_SECRET_KEYS = re.compile(r"(token|secret|password|authorization|api_key|dsn|cookie)", re.I)
# Telegram bot tokens look like 123456:ABC-DEF... and appear in Bot API URLs.
_BOT_TOKEN = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")
# The webhook route is /tg/webhook/{path_secret}; access logs and Sentry request URLs carry it.
_WEBHOOK_PATH_SECRET = re.compile(r"(/tg/webhook/)[^/\s?#\"']+")


def redact_text(value: str) -> str:
    value = _WEBHOOK_PATH_SECRET.sub(r"\1[REDACTED]", value)
    return _BOT_TOKEN.sub("[REDACTED_BOT_TOKEN]", value)


def is_secret_key(key: str) -> bool:
    """True for field/header names that hold credentials (token, secret, password...)."""
    return _SECRET_KEYS.search(key) is not None


def _redact(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in list(event_dict.items()):
        if is_secret_key(key):
            event_dict[key] = "[REDACTED]"
        elif isinstance(value, str):
            event_dict[key] = redact_text(value)
    return event_dict


class RedactingFilter(logging.Filter):
    """Redacts secrets (bot tokens, webhook path) from stdlib records (uvicorn, httpx...)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = redact_text(message)
        if record.exc_info:
            formatted = logging.Formatter().formatException(record.exc_info)
            record.exc_text = redact_text(formatted)
        if redacted != message:
            record.msg, record.args = redacted, None
        return True


class _StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Writes to whatever ``sys.stdout`` is at emit time (robust to stream swapping)."""

    @property
    def stream(self) -> Any:  # type: ignore[override]
        return sys.stdout

    @stream.setter
    def stream(self, _value: Any) -> None:
        pass


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    numeric = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    handler = _StdoutHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(numeric)
    # Under plain `uvicorn` (default log config) these loggers have their own handlers and do
    # not propagate, so the root handler's filter never sees them. Logger-level filters do.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in uv_logger.filters):
            uv_logger.addFilter(RedactingFilter())
    # httpx logs full request URLs, which contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    renderer: Any = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            _redact,  # after format_exc_info so exception text is redacted too
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        logger_factory=structlog.PrintLoggerFactory(),  # resolves sys.stdout per logger
        cache_logger_on_first_use=False,
    )
