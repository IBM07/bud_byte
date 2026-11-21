from typing import Any

from budbyte_api.observability import scrub_event

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
