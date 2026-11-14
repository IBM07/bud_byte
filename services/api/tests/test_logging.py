import logging
import sys

import pytest
import structlog

from budbyte_api.logging import RedactingFilter, configure_logging

TOKEN = "1234567890:AAH" + "x" * 32


def test_bot_token_is_redacted_from_exception_text(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json=True)
    log = structlog.get_logger()
    try:
        raise RuntimeError(f"POST https://api.telegram.org/bot{TOKEN}/sendMessage failed")
    except RuntimeError:
        log.exception("boom")
    out = capsys.readouterr().out
    assert TOKEN not in out
    assert "REDACTED" in out


def test_redacting_filter_scrubs_stdlib_message_and_traceback() -> None:
    record = logging.LogRecord(
        "uvicorn.error", logging.WARNING, __file__, 1, "url https://x/bot%s/y", (TOKEN,), None
    )
    try:
        raise ValueError(f"bot{TOKEN}")
    except ValueError:
        record.exc_info = sys.exc_info()
    assert RedactingFilter().filter(record)
    assert TOKEN not in record.getMessage()
    assert record.exc_text is not None
    assert TOKEN not in record.exc_text


def test_secret_named_fields_are_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json=True)
    structlog.get_logger().info("evt", api_key="sk-live-123", webhook_secret="abc")
    out = capsys.readouterr().out
    assert "sk-live-123" not in out
    assert '"webhook_secret": "[REDACTED]"' in out
