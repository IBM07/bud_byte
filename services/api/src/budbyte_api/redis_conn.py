"""Typed wrappers around redis-py calls whose stubs are incomplete."""

from __future__ import annotations

from typing import Any, cast

from redis.asyncio import Redis


def redis_from_url(url: str) -> Redis:
    return cast(Redis, cast(Any, Redis).from_url(url, decode_responses=True))


async def ping(redis: Redis) -> None:
    await cast(Any, redis).ping()


async def close(redis: Redis) -> None:
    await cast(Any, redis).aclose()
