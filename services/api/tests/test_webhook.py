import json

import fakeredis
import httpx
import pytest

from budbyte_api.queue import Lane

from .conftest import HEADER_SECRET, PATH_SECRET, tg_update

HDR = "X-Telegram-Bot-Api-Secret-Token"


async def _queued(r: fakeredis.FakeAsyncRedis) -> list[dict[str, object]]:
    raw = await r.lrange(Lane.INTERACTIVE.key, 0, -1)  # type: ignore[misc]
    return [json.loads(x) for x in raw]


async def test_wrong_path_secret_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post("/tg/webhook/nope", json=tg_update(), headers={HDR: HEADER_SECRET})
    assert r.status_code == 404


async def test_wrong_header_secret_is_401(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    r = await client.post(f"/tg/webhook/{PATH_SECRET}", json=tg_update(), headers={HDR: "bad"})
    assert r.status_code == 401
    assert await _queued(fake_redis) == []


async def test_valid_message_is_enqueued(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    r = await client.post(
        f"/tg/webhook/{PATH_SECRET}",
        json=tg_update(update_id=7, text="ping"),
        headers={HDR: HEADER_SECRET},
    )
    assert r.status_code == 200
    jobs = await _queued(fake_redis)
    assert len(jobs) == 1
    assert jobs[0]["type"] == "tg.message"
    assert jobs[0]["chat_id"] == 42
    assert jobs[0]["text"] == "ping"


async def test_duplicate_update_is_ignored(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    for _ in range(3):
        r = await client.post(
            f"/tg/webhook/{PATH_SECRET}", json=tg_update(update_id=9), headers={HDR: HEADER_SECRET}
        )
        assert r.status_code == 200
    assert len(await _queued(fake_redis)) == 1


async def test_non_message_update_is_acknowledged_but_not_enqueued(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    r = await client.post(
        f"/tg/webhook/{PATH_SECRET}",
        json={"update_id": 11, "edited_message": {"text": "x"}},
        headers={HDR: HEADER_SECRET},
    )
    assert r.status_code == 200
    assert await _queued(fake_redis) == []


async def test_wrong_path_with_invalid_body_is_still_404(client: httpx.AsyncClient) -> None:
    # Body validation must not run before the secret check (endpoint must be undiscoverable).
    r = await client.post("/tg/webhook/guess", json={}, headers={HDR: HEADER_SECRET})
    assert r.status_code == 404


async def test_invalid_body_with_valid_secrets_is_acknowledged(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"/tg/webhook/{PATH_SECRET}", json={"nope": True}, headers={HDR: HEADER_SECRET}
    )
    assert r.status_code == 200


async def test_failed_enqueue_releases_dedupe_key_so_telegram_can_retry(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    import budbyte_api.routes.telegram as tg_route

    async def boom(*_a: object, **_k: object) -> None:
        raise ConnectionError("redis blip")

    monkeypatch.setattr(tg_route, "enqueue", boom)
    with pytest.raises(ConnectionError):
        await client.post(
            f"/tg/webhook/{PATH_SECRET}", json=tg_update(update_id=21), headers={HDR: HEADER_SECRET}
        )
    assert await fake_redis.get("tg:update:21") is None


async def test_per_chat_rate_limit(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    from budbyte_api.routes.telegram import CHAT_RATE_LIMIT_PER_MINUTE

    for i in range(CHAT_RATE_LIMIT_PER_MINUTE + 5):
        r = await client.post(
            f"/tg/webhook/{PATH_SECRET}",
            json=tg_update(update_id=100 + i, chat_id=77),
            headers={HDR: HEADER_SECRET},
        )
        assert r.status_code == 200
    assert len(await _queued(fake_redis)) == CHAT_RATE_LIMIT_PER_MINUTE
