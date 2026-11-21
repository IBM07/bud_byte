"""Sentry setup with secret scrubbing (bot tokens in Telegram API URLs, webhook path secret)."""

from __future__ import annotations

from typing import Any

import sentry_sdk

from budbyte_api import __version__
from budbyte_api.logging import redact_text
from budbyte_api.settings import Settings, secret


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, list):
        return [_scrub(v) for v in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def scrub_event(event: Any, _hint: Any) -> Any:
    """Sentry ``before_send`` / ``before_breadcrumb`` hook: redact every string field."""
    return _scrub(event)


def init_sentry(settings: Settings) -> None:
    dsn = secret(settings.sentry_dsn)
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=settings.environment,
            release=f"budbyte-api@{__version__}",
            traces_sample_rate=0.05,
            send_default_pii=False,
            before_send=scrub_event,
            # Sampled performance transactions bypass before_send but carry request.url too.
            before_send_transaction=scrub_event,
            before_breadcrumb=scrub_event,
        )
