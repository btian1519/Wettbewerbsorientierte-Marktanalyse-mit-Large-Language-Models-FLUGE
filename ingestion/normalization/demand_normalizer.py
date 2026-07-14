"""Normalization engine — raw demand signals → 0..100 component scores.

Method (documented & outlier-robust): for each signal type, values are clipped to
the 5th/95th percentiles across all routes in the batch, then min-max scaled to
0..100::

    clipped = clip(value, p5, p95)
    score   = (clipped - p5) / (p95 - p5) * 100

Percentile clipping means a single spiking route (e.g. a viral news event) cannot
compress every other route toward zero. Google Trends is already 0..100, but is
passed through the same pipeline for consistency. Degenerate batches (all equal)
map to a neutral 50.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np

from ingestion.demand.records import RawSignal, DemandSignals

# Map a raw ``signal_type`` onto a demand-index component.
SIGNAL_TYPE_TO_COMPONENT: dict[str, str] = {
    "google_trends": "google",
    "wikipedia_views": "wikipedia",
    "eurostat_tourism": "tourism",
    "tourism": "tourism",
    "worldbank_population": "population",
    "population": "population",
    "worldbank_gdp": "gdp",
    "gdp": "gdp",
    "event": "event",
}


def robust_normalize(values: Sequence[float], low_pct: float = 5, high_pct: float = 95) -> list[float]:
    """Percentile-clipped min-max scaling to 0..100 (robust to outliers)."""
    if not values:
        return []
    arr = np.asarray(values, dtype=float)
    lo, hi = np.percentile(arr, [low_pct, high_pct])
    if hi <= lo:
        return [50.0] * len(arr)  # degenerate: everything equal
    clipped = np.clip(arr, lo, hi)
    return [float(round(v, 3)) for v in (clipped - lo) / (hi - lo) * 100.0]


def build_signal_scores(raw_signals: Sequence[RawSignal]) -> dict[tuple[str, str], DemandSignals]:
    """Aggregate raw signals per (route, component), then normalize across routes.

    Returns a mapping ``(origin, destination) -> DemandSignals`` with each present
    component scored 0..100.
    """
    # 1) mean raw value per (route, component)
    agg: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    bucket: dict[str, dict[tuple[str, str], list[float]]] = defaultdict(lambda: defaultdict(list))
    for s in raw_signals:
        comp = SIGNAL_TYPE_TO_COMPONENT.get(s.signal_type)
        if comp is None:
            continue
        bucket[comp][(s.origin_airport, s.destination_airport)].append(s.signal_value)
    for comp, per_route in bucket.items():
        for route, vals in per_route.items():
            agg[comp][route] = sum(vals) / len(vals)

    # 2) robust-normalize each component across all routes
    scores: dict[str, dict[tuple[str, str], float]] = {}
    for comp, per_route in agg.items():
        routes = list(per_route)
        normed = robust_normalize([per_route[r] for r in routes])
        scores[comp] = {routes[i]: normed[i] for i in range(len(routes))}

    # 3) assemble DemandSignals per route
    all_routes = {r for per_route in agg.values() for r in per_route}
    out: dict[tuple[str, str], DemandSignals] = {}
    for route in all_routes:
        out[route] = DemandSignals(**{comp: scores[comp].get(route) for comp in scores})
    return out
