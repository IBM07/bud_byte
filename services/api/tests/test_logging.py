import io
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


def test_uvicorn_default_access_log_is_redacted_and_still_formats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Plain `uvicorn --factory` (default log config) gives uvicorn.access its own handler with
    # propagate=False and an AccessFormatter that unpacks record.args into 5 values.
    from uvicorn.logging import AccessFormatter

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s'))
    access = logging.getLogger("uvicorn.access")
    monkeypatch.setattr(access, "handlers", [handler])
    monkeypatch.setattr(access, "propagate", False)
    monkeypatch.setattr(access, "filters", [])
    configure_logging("INFO", json=True)

    errors: list[BaseException | None] = []

    def record_error(_record: logging.LogRecord) -> None:
        errors.append(sys.exc_info()[1])

    monkeypatch.setattr(handler, "handleError", record_error)
    access.info('%s - "%s %s HTTP/%s" %d', "1.2.3.4:5", "POST", "/tg/webhook/s3cr3t", "1.1", 200)
    out = stream.getvalue()
    assert errors == []
    assert "s3cr3t" not in out
    assert '"POST /tg/webhook/[REDACTED] HTTP/1.1" 200' in out


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
