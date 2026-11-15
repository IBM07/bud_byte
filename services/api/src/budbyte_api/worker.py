"""Background worker: drains Redis job lanes."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import partial

import sentry_sdk
import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from budbyte_api.db import db_now as engine_now
from budbyte_api.db import make_engine
from budbyte_api.logging import configure_logging
from budbyte_api.observability import init_sentry
from budbyte_api.queue import Job, dequeue_with_lane, enqueue
from budbyte_api.redis_conn import close, redis_from_url
from budbyte_api.settings import Settings, secret
from budbyte_api.telegram.client import TelegramClient

log = structlog.get_logger()

MAX_ATTEMPTS = 3
REDIS_RETRY_SECONDS = 1.0

DbNow = Callable[[], Awaitable[datetime]] | None
Handler = Callable[[Job], Awaitable[None]]


async def handle_job(job: Job, *, tg: TelegramClient, db_now: DbNow) -> None:
    kind = job.get("type")
    if kind == "tg.message":
        await _pong(job, tg=tg, db_now=db_now)
    else:
        log.warning("worker.unknown_job", type=kind)


async def _pong(job: Job, *, tg: TelegramClient, db_now: DbNow) -> None:
    """Phase 1 smoke path: prove Telegram -> api -> Redis -> worker -> Postgres -> Telegram."""
    try:
        if db_now is None:
            raise RuntimeError("database not configured")
        now = await db_now()
        text = f"pong 🏓\nDB time: {now.isoformat()}"
    except Exception as exc:
        log.warning("worker.db_unavailable", error=type(exc).__name__)
        text = "pong 🏓\n(database unavailable)"
    await tg.send_message(int(job["chat_id"]), text)


async def process_one(redis: Redis, *, handler: Handler, block_seconds: float = 2.0) -> None:
    """Take one job and run it. Never raises: the worker loop must survive anything.

    Failed jobs are re-enqueued on their lane up to ``MAX_ATTEMPTS`` times.
    Known gap (Phase 2): a job in flight during a hard crash is lost; a processing list
    (BLMOVE + reaper) will make delivery at-least-once.
    """
    try:
        got = await dequeue_with_lane(redis, block_seconds)
    except ValueError:
        log.error("worker.bad_payload_dropped")
        return
    except (RedisError, OSError) as exc:
        log.warning("worker.redis_unavailable", error=type(exc).__name__)
        await asyncio.sleep(REDIS_RETRY_SECONDS)
        return
    if got is None:
        return
    lane, job = got
    try:
        await handler(job)
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        attempts = int(job.get("_attempts", 0)) + 1
        if attempts < MAX_ATTEMPTS:
            log.warning("worker.job_retry", type=job.get("type"), attempt=attempts)
            try:
                await enqueue(redis, lane, {**job, "_attempts": attempts})
            except (RedisError, OSError):
                log.exception("worker.job_requeue_failed", type=job.get("type"))
        else:
            log.exception("worker.job_dropped", type=job.get("type"), attempts=attempts)


async def run_worker(settings: Settings, stop: asyncio.Event) -> None:
    token = secret(settings.telegram_bot_token)
    if not token:
        raise RuntimeError("BUDBYTE_TELEGRAM_BOT_TOKEN is required for the worker")
    redis = redis_from_url(secret(settings.redis_url) or "")
    db_url = secret(settings.database_url)
    engine = make_engine(db_url) if db_url else None
    db_now = partial(engine_now, engine) if engine is not None else None

    log.info("worker.started")
    try:
        async with TelegramClient(token) as tg:

            async def handler(job: Job) -> None:
                await handle_job(job, tg=tg, db_now=db_now)

            while not stop.is_set():
                await process_one(redis, handler=handler)
    finally:
        await close(redis)
        if engine is not None:
            await engine.dispose()
        log.info("worker.stopped")


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level, json=settings.environment != "development")
    init_sentry(settings)

    async def _run() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:  # Windows dev machines
                signal.signal(sig, lambda _signum, _frame: stop.set())  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        await run_worker(settings, stop)

    asyncio.run(_run())
