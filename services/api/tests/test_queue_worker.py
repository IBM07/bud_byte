from datetime import UTC, datetime

import fakeredis
import httpx
import respx

from budbyte_api.queue import Lane, dequeue, enqueue
from budbyte_api.telegram.client import TelegramClient
from budbyte_api.worker import handle_job


async def test_dequeue_respects_lane_priority() -> None:
    r = fakeredis.FakeAsyncRedis(decode_responses=True)
    await enqueue(r, Lane.EVAL, {"type": "e"})
    await enqueue(r, Lane.INTERACTIVE, {"type": "i"})
    await enqueue(r, Lane.NUDGE, {"type": "n"})
    order = [(await dequeue(r, block_seconds=1)) for _ in range(3)]
    assert [j["type"] for j in order if j] == ["i", "n", "e"]
    assert await dequeue(r, block_seconds=1) is None


@respx.mock
async def test_tg_message_job_replies_pong_with_db_time() -> None:
    route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )
    fixed = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)

    async def db_now() -> datetime:
        return fixed

    async with TelegramClient("123:abc") as tg:
        await handle_job(
            {"type": "tg.message", "chat_id": 42, "text": "ping"}, tg=tg, db_now=db_now
        )

    assert route.called
    sent = route.calls.last.request
    payload = httpx.Request("POST", "x", content=sent.content).read()
    assert b'"chat_id":42' in payload.replace(b" ", b"")
    assert b"pong" in payload
    assert b"2026-11-15T12:00:00" in payload


@respx.mock
async def test_tg_message_job_still_replies_when_db_is_down() -> None:
    route = respx.post("https://api.telegram.org/bot123:abc/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    async def db_now() -> datetime:
        raise ConnectionError("db down")

    async with TelegramClient("123:abc") as tg:
        await handle_job({"type": "tg.message", "chat_id": 1, "text": "x"}, tg=tg, db_now=db_now)

    assert b"database unavailable" in route.calls.last.request.content


async def test_unknown_job_type_is_ignored_without_error() -> None:
    async with TelegramClient("123:abc") as tg:
        await handle_job({"type": "nope"}, tg=tg, db_now=None)


async def test_failed_job_is_requeued_until_max_attempts() -> None:
    from budbyte_api.worker import MAX_ATTEMPTS, process_one

    r = fakeredis.FakeAsyncRedis(decode_responses=True)
    await enqueue(r, Lane.INTERACTIVE, {"type": "tg.message", "chat_id": 1, "text": "x"})

    calls = 0

    async def failing(*_a: object, **_k: object) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("telegram timeout")

    for _ in range(MAX_ATTEMPTS + 2):
        await process_one(r, handler=failing, block_seconds=0.1)
    assert calls == MAX_ATTEMPTS
    assert await dequeue(r, block_seconds=1) is None  # dropped after MAX_ATTEMPTS, not forever


def test_redis_client_has_bounded_socket_timeouts() -> None:
    import inspect

    from budbyte_api.redis_conn import redis_from_url
    from budbyte_api.worker import process_one

    default_block = float(inspect.signature(process_one).parameters["block_seconds"].default)
    kwargs = redis_from_url("redis://localhost:6379/0").connection_pool.connection_kwargs
    assert kwargs["socket_connect_timeout"] is not None
    # Must outlast an empty BLPOP, or every idle poll would raise TimeoutError.
    assert kwargs["socket_timeout"] > default_block


async def test_bad_payload_does_not_crash_the_loop() -> None:
    from budbyte_api.worker import process_one

    r = fakeredis.FakeAsyncRedis(decode_responses=True)
    await r.rpush(Lane.INTERACTIVE.key, "not json")  # type: ignore[misc]

    async def ok(*_a: object, **_k: object) -> None:
        return None

    await process_one(r, handler=ok, block_seconds=0.1)  # must not raise
