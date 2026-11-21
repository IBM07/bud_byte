"""Integration tests against real Postgres (pgvector) + Redis.

Run in CI via service containers. Locally: set BUDBYTE_TEST_DATABASE_URL and
BUDBYTE_TEST_REDIS_URL (e.g. from `docker compose -f infra/compose.yml up db redis`).
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest
from asgi_lifespan import LifespanManager
from pydantic import SecretStr
from sqlalchemy import text

from budbyte_api.db import db_now, make_engine
from budbyte_api.main import create_app
from budbyte_api.migrate import run_migrations
from budbyte_api.queue import Lane, dequeue, enqueue
from budbyte_api.redis_conn import close, redis_from_url
from budbyte_api.settings import Settings

DB_URL = os.environ.get("BUDBYTE_TEST_DATABASE_URL")
REDIS_URL = os.environ.get("BUDBYTE_TEST_REDIS_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not (DB_URL and REDIS_URL), reason="integration env not configured"),
]


async def test_migrations_apply_and_are_safe_to_run_concurrently() -> None:
    assert DB_URL
    await asyncio.gather(*(run_migrations(DB_URL) for _ in range(3)))
    engine = make_engine(DB_URL)
    try:
        async with engine.connect() as conn:
            exts = set(
                (await conn.execute(text("SELECT extname FROM pg_extension"))).scalars().all()
            )
            version = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one()
        assert {"vector", "pgcrypto"} <= exts
        assert version == "0001"
        assert (await db_now(engine)).tzinfo is not None
    finally:
        await engine.dispose()


async def test_readyz_is_ok_with_real_dependencies() -> None:
    assert DB_URL
    assert REDIS_URL
    settings = Settings(
        environment="test",
        database_url=SecretStr(DB_URL),
        redis_url=SecretStr(REDIS_URL),
        run_migrations_on_startup=True,
    )
    app = create_app(settings)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/readyz")
    assert r.status_code == 200, r.text
    assert r.json()["checks"] == {"database": "ok", "redis": "ok"}


async def test_real_redis_queue_roundtrip() -> None:
    assert REDIS_URL
    r = redis_from_url(REDIS_URL)
    try:
        await r.delete(*(f"queue:{lane.value}" for lane in Lane))
        await enqueue(r, Lane.INGEST, {"type": "b"})
        await enqueue(r, Lane.INTERACTIVE, {"type": "a"})
        first = await dequeue(r, block_seconds=1)
        second = await dequeue(r, block_seconds=1)
        assert first == {"type": "a"}
        assert second == {"type": "b"}
    finally:
        await close(r)
