from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def ensure_partition(year: int, month: int, conn: AsyncConnection) -> None:
    if conn.dialect.name != "postgresql":
        return

    start = datetime(year, month, 1, tzinfo=UTC)
    end = (start + timedelta(days=32)).replace(day=1)
    table_name = f"rate_snapshots_{year:04d}_{month:02d}"
    query = f"""
    CREATE TABLE IF NOT EXISTS {table_name}
    PARTITION OF rate_snapshots
    FOR VALUES FROM ('{start.date()}') TO ('{end.date()}');
    """
    await conn.execute(text(query))


async def ensure_current_and_next_partitions(conn: AsyncConnection) -> None:
    now = datetime.now(UTC)
    await ensure_partition(now.year, now.month, conn)
    next_month = now.replace(day=1) + timedelta(days=32)
    await ensure_partition(next_month.year, next_month.month, conn)
