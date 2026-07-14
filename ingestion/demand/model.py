"""Demand model — rule-based Version 1 (transparent, no ML).

Demand Index V1 (weights per the brief):

    0.45·Google + 0.15·Wikipedia + 0.15·Tourism + 0.10·Population + 0.10·GDP + 0.05·Event

If some sources are missing, their weights are **dynamically renormalized** over
the present components (so the index stays on a 0..100 scale) and the resulting
``weight_coverage`` lowers the confidence score downstream.

The :class:`DemandModel` protocol is the seam for a future ML forecaster: a
``MLForecastDemandModel`` only has to implement ``compute`` and advertise its own
``version`` — nothing else in the platform changes.
"""

from __future__ import annotations

from typing import Protocol

from ingestion.demand.records import DemandComputation, DemandSignals

# Version 1 weights (must sum to 1.0).
V1_WEIGHTS: dict[str, float] = {
    "google": 0.45,
    "wikipedia": 0.15,
    "tourism": 0.15,
    "population": 0.10,
    "gdp": 0.10,
    "event": 0.05,
}


class DemandModel(Protocol):
    version: str

    def compute(self, signals: DemandSignals) -> DemandComputation: ...


class RuleBasedDemandModelV1:
    """Weighted linear combination of normalized signals with dynamic reweighting."""

    version = "v1"

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or V1_WEIGHTS

    def compute(self, signals: DemandSignals) -> DemandComputation:
        present = signals.present()
        if not present:
            return DemandComputation(
                demand_index=0.0, weight_coverage=0.0, weights_used={},
                calculation_version=self.version,
            )
        # Renormalize the weights of the present components to sum to 1.
        active = {c: self._weights[c] for c in present}
        total = sum(active.values())
        used = {c: w / total for c, w in active.items()}
        demand_index = sum(used[c] * present[c] for c in present)
        # Coverage = share of the *full* weight vector that was available.
        coverage = sum(self._weights[c] for c in present)  # weights sum to 1.0
        return DemandComputation(
            demand_index=round(demand_index, 3),
            weight_coverage=round(coverage, 3),
            weights_used={c: round(w, 3) for c, w in used.items()},
            calculation_version=self.version,
        )
