from typing import Any

import pytest
from pydantic import SecretStr

from budbyte_api.observability import scrub_event
from budbyte_api.settings import Settings

TOKEN = "1234567890:AAH" + "y" * 32


def test_scrub_event_removes_bot_tokens_everywhere() -> None:
    event: dict[str, Any] = {
        "message": f"failed bot{TOKEN}",
        "exception": {"values": [{"value": f"POST https://api.telegram.org/bot{TOKEN}/x"}]},
        "breadcrumbs": {"values": [{"data": {"url": f"https://api.telegram.org/bot{TOKEN}/y"}}]},
        "extra": {"nested": [f"{TOKEN}", 3, None]},
    }
    out = scrub_event(event, {})
    assert out is not None
    assert TOKEN not in repr(out)
    assert out["extra"]["nested"][1] == 3


def test_init_sentry_scrubs_transactions_too(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sampled performance transactions skip before_send; they carry request.url as well.
    import budbyte_api.observability as obs

    seen: dict[str, Any] = {}
    monkeypatch.setattr(obs.sentry_sdk, "init", lambda **kw: seen.update(kw))  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    obs.init_sentry(Settings(environment="test", sentry_dsn=SecretStr("https://k@o0.ingest.io/1")))
    assert seen["before_send"] is scrub_event
    assert seen["before_send_transaction"] is scrub_event


def test_scrub_event_removes_webhook_path_secret_from_request_url() -> None:
    event: dict[str, Any] = {"request": {"url": "https://api.example.com/tg/webhook/s3cr3t"}}
    out = scrub_event(event, {})
    assert out["request"]["url"] == "https://api.example.com/tg/webhook/[REDACTED]"
