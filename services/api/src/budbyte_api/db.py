"""Database engine helpers (async SQLAlchemy + asyncpg, Neon-compatible)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# libpq-only query params that asyncpg rejects
_LIBPQ_ONLY = {"sslmode", "channel_binding", "options", "target_session_attrs"}


def to_asyncpg_url(url: str) -> tuple[str, dict[str, Any]]:
    """Convert a libpq-style URL (as Neon/Render hand out) to an asyncpg SQLAlchemy URL.

    Returns the URL and the ``connect_args`` needed to preserve SSL intent.
    """
    parts = urlsplit(url)
    scheme = "postgresql+asyncpg"
    query = dict(parse_qsl(parts.query))
    connect_args: dict[str, Any] = {}
    sslmode = query.get("sslmode")
    if sslmode and sslmode != "disable":
        connect_args["ssl"] = "require"
    if "-pooler" in (parts.hostname or ""):
        # Transaction-mode poolers (Neon/PgBouncer) can hand each statement a different
        # backend, so asyncpg's per-connection prepared-statement cache must be off.
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = _unique_statement_name
    kept = {k: v for k, v in query.items() if k not in _LIBPQ_ONLY}
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(kept), "")), connect_args


def _unique_statement_name() -> str:
    return f"__asyncpg_{uuid4().hex}__"


def make_engine(database_url: str) -> AsyncEngine:
    url, connect_args = to_asyncpg_url(database_url)
    # Small pool + short recycle so Neon can scale to zero between bursts.
    return create_async_engine(
        url,
        connect_args=connect_args,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=300,
    )


async def db_now(engine: AsyncEngine) -> datetime:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT now()"))
        value = result.scalar_one()
    assert isinstance(value, datetime)
    return value
