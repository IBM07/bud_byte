"""Telegram webhook: verify, de-duplicate, rate-limit, enqueue. Must answer fast (no LLM work)."""

from __future__ import annotations

import hmac
from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from budbyte_api.queue import Lane, enqueue
from budbyte_api.settings import Settings, secret

router = APIRouter(tags=["telegram"])
log = structlog.get_logger()

DEDUPE_TTL_SECONDS = 24 * 3600
CHAT_RATE_LIMIT_PER_MINUTE = 20


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
    # INCR and TTL in one round trip, then set the window only when the key has no TTL.
    # This self-heals a counter left without a TTL (which would rate-limit the chat forever)
    # and never slides an existing window. Plain commands, so any Redis version works.
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()
    if int(ttl) < 0:
        await redis.expire(key, 60)
    return int(count) <= CHAT_RATE_LIMIT_PER_MINUTE


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

    redis = request.app.state.redis
    dedupe_key = f"tg:update:{update.update_id}"
    first_time = await redis.set(dedupe_key, "1", nx=True, ex=DEDUPE_TTL_SECONDS)
    if not first_time:
        log.info("tg.update.duplicate", update_id=update.update_id)
        return Ack(ok=True)

    msg = update.message
    # v1 handles private chats only; groups are ignored (abuse surface).
    if msg is None or msg.chat.type != "private":
        return Ack(ok=True)

    job: dict[str, Any] = {
        "type": "tg.message",
        "update_id": update.update_id,
        "chat_id": msg.chat.id,
        "message_id": msg.message_id,
        "text": msg.text or "",
    }
    try:
        if not await _within_rate_limit(redis, msg.chat.id):
            log.warning("tg.update.rate_limited", chat_id=msg.chat.id)
            return Ack(ok=True)
        await enqueue(redis, Lane.INTERACTIVE, job)
    except Exception:
        # Anything failing before the job is durably queued must release the dedupe key,
        # so Telegram's retry of this update is processed instead of dropped as a duplicate.
        await redis.delete(dedupe_key)
        raise
    log.info("tg.update.enqueued", update_id=update.update_id)
    return Ack(ok=True)
