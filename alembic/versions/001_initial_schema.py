"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_snapshots (
                id BIGSERIAL PRIMARY KEY,
                pair VARCHAR(7) NOT NULL,
                rate NUMERIC(18, 8) NOT NULL,
                source_count SMALLINT NOT NULL,
                confidence VARCHAR(15) NOT NULL,
                sources_used JSONB NOT NULL DEFAULT '[]'::jsonb,
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            ) PARTITION BY RANGE (recorded_at)
            """
        )
    else:
        op.create_table(
            "rate_snapshots",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("pair", sa.String(length=7), nullable=False),
            sa.Column("rate", sa.Numeric(18, 8), nullable=False),
            sa.Column("source_count", sa.SmallInteger(), nullable=False),
            sa.Column("confidence", sa.String(length=15), nullable=False),
            sa.Column("sources_used", sa.JSON(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            if_not_exists=True,
        )

    op.create_index(
        "ix_rate_snapshots_pair_recorded_at",
        "rate_snapshots",
        ["pair", "recorded_at"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_rate_snapshots_pair_recorded_at", table_name="rate_snapshots")
    op.drop_table("rate_snapshots")
