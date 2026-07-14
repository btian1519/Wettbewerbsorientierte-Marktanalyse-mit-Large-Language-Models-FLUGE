"""Demand Data Platform V1 — persistent tables.

Three additive tables implement the demand pipeline (raw → normalized →
calibration) exactly as specified. They are separate from the demo tables and
from the earlier generic observation tables; the demo mode is unaffected.

Every normalized row is versioned (``calculation_version`` + ``snapshot_date``)
so demand history is preserved for later trend analysis / ML training. IATA codes
are indexed strings (no hard FKs) so ingestion never fails on an as-yet-unknown
airport.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawDemandSignal(Base):
    """Every unfiltered demand signal, exactly as fetched from a source."""

    __tablename__ = "demand_raw_signal"
    __table_args__ = (
        Index("ix_raw_signal_od", "origin_airport", "destination_airport"),
        Index("ix_raw_signal_type_week", "signal_type", "week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    origin_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)   # google_trends, wikipedia_views, ...
    signal_value: Mapped[float] = mapped_column(Float, nullable=False)
    search_term: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    week: Mapped[str | None] = mapped_column(String(8), nullable=True)
    snapshot_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class DemandNormalized(Base):
    """The standardized demand output — one row per (route, week, version, snapshot)."""

    __tablename__ = "demand_normalized"
    __table_args__ = (
        Index("ix_norm_od_week", "origin_airport", "destination_airport", "week"),
        Index("ix_norm_route_week_ver", "route_id", "week", "calculation_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    origin_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_airport: Mapped[str] = mapped_column(String(3), nullable=False)
    week: Mapped[str] = mapped_column(String(8), index=True, nullable=False)

    # Component scores (0..100, NULL when the source is missing).
    google_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    wikipedia_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tourism_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    population_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gdp_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    demand_index: Mapped[float] = mapped_column(Float, nullable=False)              # 0..100
    estimated_weekly_passengers: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)          # 0..1

    calculation_version: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class DemandCalibration(Base):
    """Calibration factors mapping a demand index onto absolute passengers."""

    __tablename__ = "demand_calibration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    reference_passengers: Mapped[float] = mapped_column(Float, nullable=False)
    reference_source: Mapped[str] = mapped_column(String(24), nullable=False)       # eurostat|historical|demo
    calibration_factor: Mapped[float] = mapped_column(Float, nullable=False)        # pax per index point
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
