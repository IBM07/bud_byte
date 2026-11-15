"""Baseline: required Postgres extensions.

Revision ID: 0001
Revises:
Create Date: 2026-11-15
"""

from __future__ import annotations

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # pgvector: memory embeddings
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # gen_random_bytes, digest


def downgrade() -> None:
    # Extensions are shared infrastructure; never drop them automatically.
    pass
