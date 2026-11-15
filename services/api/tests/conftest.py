from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import fakeredis
import httpx
import pytest
from asgi_lifespan import LifespanManager
from pydantic import SecretStr

from budbyte_api.main import create_app
from budbyte_api.settings import Settings

# Tests must never pick up the developer's real .env (DB URLs, Sentry DSN, bot tokens).
Settings.model_config["env_file"] = None

PATH_SECRET = "path-secret-123"
HEADER_SECRET = "header-secret-456"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url=None,
        redis_url=SecretStr("redis://unused:6379/0"),
        telegram_bot_token=SecretStr("123:abc"),
        telegram_webhook_secret=SecretStr(HEADER_SECRET),
        telegram_path_secret=SecretStr(PATH_SECRET),
        run_migrations_on_startup=False,
    )


@pytest.fixture
def fake_redis() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.fixture
async def client(
    settings: Settings, fake_redis: fakeredis.FakeAsyncRedis
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings, redis=fake_redis)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


def tg_update(update_id: int = 1, text: str = "hi", chat_id: int = 42) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 10,
            "date": 1_700_000_000,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id, "is_bot": False, "first_name": "T"},
            "text": text,
        },
    }
