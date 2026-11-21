"""Telegram webhook: verify, de-duplicate, rate-limit, enqueue. Must answer fast (no LLM work)."""

from __future__ import annotations

import hmac
from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError
from redis.exceptions import WatchError

from budbyte_api.queue import Lane, encode_job
from budbyte_api.settings import Settings, secret

router = APIRouter(tags=["telegram"])
log = structlog.get_logger()

DEDUPE_TTL_SECONDS = 24 * 3600
CHAT_RATE_LIMIT_PER_MINUTE = 20
RATE_WINDOW_SECONDS = 60


class TgChat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    type: str


class TgMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: int
    chat: TgChat
    text: str | None = None


class TgUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    update_id: int
    message: TgMessage | None = None


class Ack(BaseModel):
    ok: bool


def _eq(a: str | None, b: str | None) -> bool:
    return a is not None and b is not None and hmac.compare_digest(a.encode(), b.encode())


async def _within_rate_limit(redis: Any, chat_id: int) -> bool:
    """Fixed-window limiter per chat. Protects free-tier quotas from a single noisy chat."""
    key = f"rl:tg:chat:{chat_id}"
    # One MULTI: create the window with its TTL (SET NX EX) and count in it, so a new counter
    # never exists without a TTL and concurrent requests cannot shift the window.
    async with redis.pipeline(transaction=True) as pipe:
        pipe.set(key, 0, ex=RATE_WINDOW_SECONDS, nx=True)
        pipe.incr(key)
        pipe.ttl(key)
        _, count, ttl = await pipe.execute()
    if int(ttl) < 0:
        # Self-heal a legacy counter stuck without a TTL (it would rate-limit the chat forever).
        await redis.expire(key, RATE_WINDOW_SECONDS)
    return int(count) <= CHAT_RATE_LIMIT_PER_MINUTE


async def _claim_and_enqueue(redis: Any, dedupe_key: str, job: dict[str, Any]) -> bool:
    """Mark the update seen AND queue its job in one transaction. False if already seen.

    Both writes land together or not at all, so a failure (or a lost reply) can never leave
    an update marked "seen" with no job queued, and no cleanup call is needed.
    """
    async with redis.pipeline(transaction=True) as pipe:
        try:
            await pipe.watch(dedupe_key)
            if await pipe.exists(dedupe_key):
                return False
            pipe.multi()
            pipe.set(dedupe_key, "1", ex=DEDUPE_TTL_SECONDS)
            pipe.rpush(Lane.INTERACTIVE.key, encode_job(job))
            await pipe.execute()
        except WatchError:
            # Usually a concurrent delivery of the same update claimed it first, but redis-py
            # also raises WatchError when the connection drops mid-WATCH. Ack as a duplicate
            # only when the mark really exists; otherwise fail (500) so Telegram retries.
            if await redis.exists(dedupe_key):
                return False
            raise
    return True


@router.post("/tg/webhook/{path_secret}", response_model=Ack, include_in_schema=False)
async def telegram_webhook(
    path_secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Ack:
    settings: Settings = request.app.state.settings
    # Secrets are checked BEFORE the body is parsed, so a wrong path is always a plain 404
    # (no 422 validation details that would reveal the endpoint exists).
    if not _eq(path_secret, secret(settings.telegram_path_secret)):
        raise HTTPException(status_code=404)
    if not _eq(x_telegram_bot_api_secret_token, secret(settings.telegram_webhook_secret)):
        raise HTTPException(status_code=401)

    try:
        update = TgUpdate.model_validate(await request.json())
    except (ValidationError, ValueError):
        # Acknowledge so Telegram does not retry an update we will never understand.
        log.warning("tg.update.unparseable")
        return Ack(ok=True)

    msg = update.message
    # v1 handles private chats only; groups are ignored (abuse surface).
    if msg is None or msg.chat.type != "private":
        return Ack(ok=True)

    redis = request.app.state.redis
    dedupe_key = f"tg:update:{update.update_id}"
    # Cheap early exit so Telegram retries of a queued update don't spend the chat's quota.
    # Not the source of truth: _claim_and_enqueue re-checks atomically.
    if await redis.exists(dedupe_key):
        log.info("tg.update.duplicate", update_id=update.update_id)
        return Ack(ok=True)
    if not await _within_rate_limit(redis, msg.chat.id):
        log.warning("tg.update.rate_limited", chat_id=msg.chat.id)
        return Ack(ok=True)

    job: dict[str, Any] = {
        "type": "tg.message",
        "update_id": update.update_id,
        "chat_id": msg.chat.id,
        "message_id": msg.message_id,
        "text": msg.text or "",
    }
    # Any exception propagates as a 500 with nothing claimed, so Telegram's retry is processed.
    if not await _claim_and_enqueue(redis, dedupe_key, job):
        log.info("tg.update.duplicate", update_id=update.update_id)
        return Ack(ok=True)
    log.info("tg.update.enqueued", update_id=update.update_id)
    return Ack(ok=True)
