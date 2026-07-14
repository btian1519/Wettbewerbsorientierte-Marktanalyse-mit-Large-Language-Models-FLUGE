"""Historical / temporal models for the live-data platform.

These tables are **additive** and completely separate from the demo tables
(``route_weeks`` / ``airline_offers``), which are never touched. Every row carries
a temporal dimension so past snapshots are preserved and trends (demand,
capacity, market change) can be analysed later, even though the UI currently only
consumes the latest week.

Design notes:
* ``origin_iata`` / ``dest_iata`` / ``airline_iata`` are indexed strings, **not**
  hard foreign keys — a live source may reference an airport/airline before we
  have catalogued it, and we must never fail ingestion or overwrite master data.
* Column types are chosen to be PostgreSQL-compatible; coordinates on
  :class:`~database.models.airport.Airport` remain plain floats today but can move
  to PostGIS geometry later without touching these tables.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Route(Base):
    """Canonical directed O-D route for live observations."""

    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint("origin_iata", "dest_iata", name="uq_route_od"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origin_iata: Mapped[str] = mapped_column(String(3), index=True, nullable=False)
    dest_iata: Mapped[str] = mapped_column(String(3), index=True, nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    continent_category: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class SupplyObservation(Base):
    """A single carrier's capacity on a route for one week/snapshot."""

    __tablename__ = "supply_observations"
    __table_args__ = (
        Index("ix_supply_route_week", "route_id", "week"),
        Index("ix_supply_snapshot", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    airline_iata: Mapped[str] = mapped_column(String(3), index=True, nullable=False)

    week: Mapped[str] = mapped_column(String(8), index=True, nullable=False)          # ISO year-week
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)             # weekly seat capacity
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)                   # flights per week
    aircraft_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    average_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(16), nullable=True)

    source: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class DemandObservation(Base):
    """Estimated demand for a route for one week/snapshot."""

    __tablename__ = "demand_observations"
    __table_args__ = (
        Index("ix_demand_route_week", "route_id", "week"),
        Index("ix_demand_snapshot", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    week: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    passengers: Mapped[float | None] = mapped_column(Float, nullable=True)            # estimated weekly pax
    demand_index: Mapped[float | None] = mapped_column(Float, nullable=True)          # normalised 0..1(+)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)      # 0..1

    source: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class TrendObservation(Base):
    """Raw demand-proxy value (e.g. a Google-Trends keyword reading)."""

    __tablename__ = "trend_observations"
    __table_args__ = (Index("ix_trend_route_week", "route_id", "week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    week: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    timeframe: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class SyncRun(Base):
    """Audit record of a single sync job execution (append-only history)."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    coverage_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)  # e.g. "Global"
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # running|success|error|skipped
    records_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(String(512), nullable=True)


class SyncState(Base):
    """Current coverage state per (data source, category) — upserted each sync.

    Answers, per the brief: when were the data last updated, from which source,
    which market areas are synced, and with what status. One row per source/
    category holds the *latest* state (``sync_runs`` keeps the full history).
    """

    __tablename__ = "sync_state"
    __table_args__ = (UniqueConstraint("data_source", "category", name="uq_sync_state"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_source: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    coverage_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False)
    records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sync_timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
