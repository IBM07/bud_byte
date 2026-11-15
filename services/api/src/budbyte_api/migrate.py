"""Run Alembic migrations safely from several processes at once (advisory lock)."""

from __future__ import annotations

from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection

from budbyte_api.db import make_engine

log = structlog.get_logger()

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
# Arbitrary constant shared by every BudByte process: "BUDBYTE" in hex-ish.
ADVISORY_LOCK_KEY = 0x0B0DB17E


def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


def _upgrade(connection: Connection) -> None:
    cfg = alembic_config()
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


async def run_migrations(database_url: str) -> None:
    """Upgrade to head inside ONE transaction guarded by a transaction-scoped advisory lock.

    ``pg_advisory_xact_lock`` is released automatically on commit or rollback, so it is safe
    behind a transaction-mode pooler (Neon ``-pooler`` / PgBouncer) and a failed migration
    can never leave the lock held or mask the original error.
    """
    engine = make_engine(database_url)
    try:
        async with engine.connect() as conn, conn.begin():
            await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ADVISORY_LOCK_KEY})
            await conn.run_sync(_upgrade)
        log.info("migrations.done")
    finally:
        await engine.dispose()
