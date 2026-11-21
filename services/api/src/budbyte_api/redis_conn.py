"""Typed wrappers around redis-py calls whose stubs are incomplete."""

from __future__ import annotations

from typing import Any, cast

from redis.asyncio import Redis

# Bound every network wait so a silently dead connection cannot hang the worker forever.
# SOCKET_TIMEOUT must stay above the worker's BLPOP block time (2s) or idle polls would raise.
SOCKET_CONNECT_TIMEOUT_SECONDS = 5.0
SOCKET_TIMEOUT_SECONDS = 10.0


def redis_from_url(url: str) -> Redis:
    return cast(
        Redis,
        cast(Any, Redis).from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=SOCKET_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=SOCKET_TIMEOUT_SECONDS,
        ),
    )


async def ping(redis: Redis) -> None:
    await cast(Any, redis).ping()


async def close(redis: Redis) -> None:
    await cast(Any, redis).aclose()
