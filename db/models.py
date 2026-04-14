from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, SmallInteger, String
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RateSnapshot(Base):
    __tablename__ = "rate_snapshots"
    __table_args__ = (
        Index("ix_rate_snapshots_pair_recorded_at", "pair", "recorded_at"),
        {"postgresql_partition_by": "RANGE (recorded_at)"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    pair: Mapped[str] = mapped_column(String(7), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence: Mapped[str] = mapped_column(String(15), nullable=False)
    sources_used: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
