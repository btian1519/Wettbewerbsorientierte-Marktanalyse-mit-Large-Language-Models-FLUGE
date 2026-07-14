"""Calibration layer — turns a 0..100 demand index into absolute passengers.

Two regimes:

* **Calibrated** — a reference passenger figure exists (Eurostat, historical data,
  or the existing demo supply/demand). ``calibration_factor = reference_pax /
  reference_index`` and ``estimate = demand_index × factor``.
* **Fallback** — no reference for the route. A transparent gravity-style estimate
  from distance, origin/destination size and macro factors, with a **lower
  confidence score**.

The confidence score (0..1) rises with signal coverage, calibration and history.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.utils import clamp

_FALLBACK_BASE_PAX = 3000.0  # weekly pax at demand_index=100 under neutral context


@dataclass(frozen=True, slots=True)
class CalibrationContext:
    """Optional context for the fallback estimate (all default to neutral)."""

    distance_km: float | None = None
    origin_size: float = 1.0        # relative airport size (~1 = average)
    dest_size: float = 1.0
    population_factor: float = 1.0  # ~1 = average; >1 = larger market
    gdp_factor: float = 1.0


class CalibrationLayer:
    # ------------------------------------------------------------------ #
    # Calibrated path
    # ------------------------------------------------------------------ #
    @staticmethod
    def calibration_factor(reference_passengers: float, reference_index: float) -> float:
        """Passengers per index point, so estimate(reference_index) == reference_pax."""
        return reference_passengers / max(reference_index, 1.0)

    @staticmethod
    def estimate_calibrated(demand_index: float, calibration_factor: float) -> float:
        return round(demand_index * calibration_factor, 1)

    # ------------------------------------------------------------------ #
    # Fallback path
    # ------------------------------------------------------------------ #
    @staticmethod
    def fallback_estimate(demand_index: float, ctx: CalibrationContext | None = None) -> float:
        ctx = ctx or CalibrationContext()
        idx = demand_index / 100.0
        size = (max(ctx.origin_size, 0.01) * max(ctx.dest_size, 0.01)) ** 0.5
        dist = 1.0
        if ctx.distance_km:
            dist = (2000.0 / (ctx.distance_km + 1500.0)) ** 0.30
        macro = (max(ctx.population_factor, 0.01) * max(ctx.gdp_factor, 0.01)) ** 0.5
        return round(_FALLBACK_BASE_PAX * idx * size * dist * macro, 1)

    # ------------------------------------------------------------------ #
    # Confidence
    # ------------------------------------------------------------------ #
    @staticmethod
    def confidence(weight_coverage: float, *, calibrated: bool, has_history: bool) -> float:
        """0..1 confidence. Proxy-only ≈ 0.48; trends+reference+history ≈ 0.9+."""
        score = 0.30 + 0.40 * weight_coverage
        if calibrated:
            score += 0.20
        if has_history:
            score += 0.10
        return round(clamp(score, 0.05, 0.98), 3)
