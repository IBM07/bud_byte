"""Alembic environment. Runs on a connection handed in by ``budbyte_api.migrate``."""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection

from budbyte_api.db import make_engine

config = context.config
target_metadata = None  # models arrive in Phase 2; migrations are hand-written


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_standalone() -> None:
    url = os.environ["BUDBYTE_DATABASE_URL"]
    engine = make_engine(url)
    try:
        async with engine.connect() as conn:
            await conn.run_sync(_run)
            await conn.commit()
    finally:
        await engine.dispose()


connection = config.attributes.get("connection")
if connection is not None:
    _run(connection)
else:  # invoked via the alembic CLI
    asyncio.run(_run_standalone())
