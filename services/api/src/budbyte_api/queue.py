"""Redis-backed job lanes. Higher-priority lanes are always drained first."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, cast

from redis.asyncio import Redis


class Lane(Enum):
    INTERACTIVE = "interactive"
    NUDGE = "nudge"
    INGEST = "ingest"
    EVAL = "eval"

    @property
    def key(self) -> str:
        return f"queue:{self.value}"


PRIORITY: tuple[Lane, ...] = (Lane.INTERACTIVE, Lane.NUDGE, Lane.INGEST, Lane.EVAL)

Job = dict[str, Any]


async def enqueue(redis: Redis, lane: Lane, job: Job) -> None:
    await cast(Any, redis.rpush(lane.key, json.dumps(job, separators=(",", ":"))))


_LANE_BY_KEY = {lane.key: lane for lane in Lane}


async def dequeue_with_lane(redis: Redis, block_seconds: float = 5.0) -> tuple[Lane, Job] | None:
    """Block up to ``block_seconds`` for the next job, highest-priority lane first.

    Raises ``ValueError`` for a payload that is not a JSON object (the item is already removed).
    """
    # BLPOP checks keys in order, which gives us strict lane priority.
    item = await cast(Any, redis.blpop([lane.key for lane in PRIORITY], timeout=block_seconds))
    if item is None:
        return None
    key, raw = item
    job = json.loads(raw)
    if not isinstance(job, dict):
        raise ValueError("job payload is not a JSON object")
    return _LANE_BY_KEY[key], cast(Job, job)


async def dequeue(redis: Redis, block_seconds: float = 5.0) -> Job | None:
    got = await dequeue_with_lane(redis, block_seconds)
    return got[1] if got else None
