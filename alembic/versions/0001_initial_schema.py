"""Initial schema — all tables.

Revision ID: 0001
Revises:
Create Date: 2026-04-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (optional — skip if not available)
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        pass  # pgvector optional in dev

    # All tables are created via SQLAlchemy metadata in env.py autogenerate.
    # This migration is a marker — run `alembic revision --autogenerate -m "schema"`
    # for full DDL after connecting to a real database.
    pass


def downgrade() -> None:
    pass
