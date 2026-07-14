"""Persistence for the Demand Data Platform (raw / normalized / calibration)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import func, insert, select

from database.base import session_scope
from database.models import DemandCalibration, DemandNormalized, RawDemandSignal
from shared.logging_config import get_logger

log = get_logger("database.demand_repo")


@dataclass(frozen=True, slots=True)
class NormalizedDemand:
    """Neutral read-model for a route/week demand estimate (no ingestion types)."""

    estimated_weekly_passengers: float
    demand_index: float
    confidence_score: float


class SqlAlchemyDemandRepository:
    # -- writes --------------------------------------------------------- #
    def save_raw_signals(self, rows: Sequence[dict]) -> int:
        if not rows:
            return 0
        with session_scope() as s:
            s.execute(insert(RawDemandSignal), list(rows))
        return len(rows)

    def save_normalized(self, rows: Sequence[dict]) -> int:
        if not rows:
            return 0
        with session_scope() as s:
            s.execute(insert(DemandNormalized), list(rows))
        log.info("Saved %d normalized demand rows", len(rows))
        return len(rows)

    def save_calibration(self, rows: Sequence[dict]) -> int:
        if not rows:
            return 0
        with session_scope() as s:
            s.execute(insert(DemandCalibration), list(rows))
        return len(rows)

    # -- calibration lookups ------------------------------------------- #
    def calibration_factor(self, route_id: int) -> float | None:
        with session_scope() as s:
            return s.scalar(
                select(DemandCalibration.calibration_factor)
                .where(DemandCalibration.route_id == route_id)
                .order_by(DemandCalibration.created_at.desc())
                .limit(1)
            )

    def has_history(self, origin: str, destination: str, week: str) -> bool:
        with session_scope() as s:
            return s.scalar(
                select(func.count()).select_from(DemandNormalized).where(
                    DemandNormalized.origin_airport == origin,
                    DemandNormalized.destination_airport == destination,
                    DemandNormalized.week == week,
                )
            ) > 0

    # -- the analysis-engine contract ---------------------------------- #
    def get_weekly_demand(self, origin: str, destination: str, week: str) -> NormalizedDemand | None:
        """Latest normalized demand for a route/week (newest snapshot wins)."""
        with session_scope() as s:
            row = s.execute(
                select(DemandNormalized)
                .where(
                    DemandNormalized.origin_airport == origin,
                    DemandNormalized.destination_airport == destination,
                    DemandNormalized.week == week,
                )
                .order_by(DemandNormalized.snapshot_date.desc(), DemandNormalized.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if row is None:
                return None
            return NormalizedDemand(
                estimated_weekly_passengers=row.estimated_weekly_passengers,
                demand_index=row.demand_index,
                confidence_score=row.confidence_score,
            )

    # -- status (dev footer: Demand Status) ---------------------------- #
    def status(self) -> dict:
        with session_scope() as s:
            normalized = int(s.scalar(select(func.count()).select_from(DemandNormalized)) or 0)
            raw = int(s.scalar(select(func.count()).select_from(RawDemandSignal)) or 0)
            od_pairs = int(s.scalar(
                select(func.count(func.distinct(
                    DemandNormalized.origin_airport + "-" + DemandNormalized.destination_airport
                )))
            ) or 0)
            last_sync: datetime | None = s.scalar(select(func.max(DemandNormalized.created_at)))
            avg_conf = s.scalar(select(func.avg(DemandNormalized.confidence_score)))
            last_version = s.scalar(
                select(DemandNormalized.calculation_version)
                .order_by(DemandNormalized.created_at.desc()).limit(1)
            )
            return {
                "od_pairs": od_pairs,
                "signals": raw,
                "normalized_rows": normalized,
                "last_demand_sync": last_sync,
                "last_calculation_version": last_version,
                "avg_confidence": round(float(avg_conf), 3) if avg_conf is not None else None,
            }
