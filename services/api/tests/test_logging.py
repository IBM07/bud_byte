import logging
import sys

import pytest
import structlog

from budbyte_api.logging import RedactingFilter, configure_logging, redact_text

TOKEN = "1234567890:AAH" + "x" * 32


def test_webhook_path_secret_is_redacted_but_route_kept() -> None:
    line = '127.0.0.1 - "POST /tg/webhook/s3cr3t-Path_value?x=1 HTTP/1.1" 200'
    out = redact_text(line)
    assert "s3cr3t-Path_value" not in out
    assert "/tg/webhook/[REDACTED]?x=1 HTTP/1.1" in out


def test_access_log_record_has_webhook_path_secret_scrubbed() -> None:
    # uvicorn.access formats the path from record.args, so the filter must catch it there.
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "POST", "/tg/webhook/s3cr3t", "1.1", 200),
        None,
    )
    assert RedactingFilter().filter(record)
    assert "s3cr3t" not in record.getMessage()


def test_uvicorn_loggers_redact_even_with_their_own_handlers() -> None:
    # Plain `uvicorn --factory` (default log config) gives uvicorn.access its own handler with
    # propagate=False, so a filter on the root handler alone would never see access lines.
    configure_logging("INFO", json=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        assert any(isinstance(f, RedactingFilter) for f in logging.getLogger(name).filters)


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
