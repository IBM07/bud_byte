"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from budbyte_api import __version__
from budbyte_api.db import make_engine
from budbyte_api.logging import configure_logging
from budbyte_api.migrate import run_migrations
from budbyte_api.redis_conn import close, ping, redis_from_url
from budbyte_api.routes import health, telegram
from budbyte_api.settings import Settings, secret

log = structlog.get_logger()


def init_sentry(settings: Settings) -> None:
    dsn = secret(settings.sentry_dsn)
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=settings.environment,
            release=f"budbyte-api@{__version__}",
            traces_sample_rate=0.05,
            send_default_pii=False,
        )


def create_app(
    settings: Settings | None = None,
    *,
    redis: Redis | None = None,
    engine: AsyncEngine | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        configure_logging(settings.log_level, json=settings.environment != "development")
        init_sentry(settings)

        own_redis = redis is None
        r = redis or redis_from_url(secret(settings.redis_url) or "")

        db_url = secret(settings.database_url)
        eng = engine or (make_engine(db_url) if db_url else None)
        if db_url and settings.run_migrations_on_startup:
            await run_migrations(db_url)

        async def check_db() -> None:
            assert eng is not None
            async with eng.connect() as conn:
                await conn.execute(text("SELECT 1"))

        async def check_redis() -> None:
            await ping(r)

        app.state.settings = settings
        app.state.redis = r
        app.state.engine = eng
        app.state.readiness_checks = {
            "database": check_db if eng is not None else None,
            "redis": check_redis,
        }
        log.info("api.started", environment=settings.environment, version=__version__)
        try:
            yield
        finally:
            if own_redis:
                await close(r)
            if eng is not None and engine is None:
                await eng.dispose()

    app = FastAPI(
        title="BudByte API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_prod_like else "/docs",
        redoc_url=None,
    )
    app.include_router(health.router)
    app.include_router(telegram.router)
    return app


def app_factory() -> FastAPI:
    """Entry point for ``uvicorn --factory``."""
    return create_app()
