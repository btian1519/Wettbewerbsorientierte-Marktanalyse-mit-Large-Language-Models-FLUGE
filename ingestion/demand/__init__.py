"""Demand Data Platform V1 — connectors, model, records.

Rule-based, transparent demand estimation (no ML) with an ML-ready seam
(:class:`DemandModel`). Orchestration lives in
``backend.services.demand_service.DemandService``; the analysis engine consumes
demand only via ``DemandService.get_weekly_demand``.
"""

from ingestion.demand.model import (
    V1_WEIGHTS,
    DemandModel,
    RuleBasedDemandModelV1,
)
from ingestion.demand.records import (
    DemandSignals,
    RawSignal,
    RouteContext,
    WeeklyDemand,
)

__all__ = [
    "DemandModel",
    "RuleBasedDemandModelV1",
    "V1_WEIGHTS",
    "DemandSignals",
    "RawSignal",
    "RouteContext",
    "WeeklyDemand",
]
