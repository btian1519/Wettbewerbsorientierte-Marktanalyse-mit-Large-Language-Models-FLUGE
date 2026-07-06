"""Route-level filters driven by the sidebar 'Additional Filters'.

Currently a single active threshold (minimum distance efficiency); the function
signature and structure make adding further threshold filters (from
``FilterSettings.extra``) a local change. Parameter-style inputs
(``marge_average``, ``network_availability``) are *not* filters — they belong to
the benefit formula and are applied in the engine.
"""

from __future__ import annotations

from typing import Sequence

from backend.analysis.engine import distance_efficiency
from backend.dto import FilterSettings
from database.repository.interfaces import RouteRead


def apply_filters(routes: Sequence[RouteRead], filters: FilterSettings) -> list[RouteRead]:
    threshold = filters.min_distance_efficiency
    if threshold <= 0.0:
        return list(routes)
    return [r for r in routes if distance_efficiency(r.distance_km) >= threshold]
