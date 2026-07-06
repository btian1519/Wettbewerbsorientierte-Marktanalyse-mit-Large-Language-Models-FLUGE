"""Price (EUR) resolution with the mandated priority chain.

Priority per the brief:
  1. Average price of the **selected airline** on the route.
  2. Otherwise the average price of **other airlines** on the route.
  3. Otherwise the selected airline's average over **similar distances** within
     the same continent scope.

A final safety net (scope-wide mean) guarantees a non-null price for unserved
routes when the airline has no priced routes at all. The resolver is built once
per analysis over the in-scope route set, so all lookups are in-memory.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Sequence

from database.repository.interfaces import RouteRead
from shared.utils import mean

# Source tags surfaced to the UI / dev footer.
SRC_AIRLINE = "airline"
SRC_ROUTE_OTHERS = "route_others"
SRC_DISTANCE_PROXY = "distance_proxy"
SRC_SCOPE_MEAN = "scope_mean"
SRC_NONE = "unavailable"

_SIMILAR_DISTANCE_BAND = 0.25  # ±25% distance window for fallback (3)


@dataclass(frozen=True, slots=True)
class ResolvedPrice:
    price_eur: float
    source: str


class PriceResolver:
    def __init__(self, scope_routes: Sequence[RouteRead], airline_iata: str) -> None:
        self._airline = airline_iata
        # Sorted (distance, price) points for the selected airline — for fallback 3.
        points: list[tuple[float, float]] = []
        all_prices: list[float] = []
        for r in scope_routes:
            for o in r.offers:
                all_prices.append(o.avg_price_eur)
                if o.airline_iata == airline_iata:
                    points.append((r.distance_km, o.avg_price_eur))
        points.sort(key=lambda p: p[0])
        self._distances = [p[0] for p in points]
        self._prices = [p[1] for p in points]
        self._scope_mean = mean(all_prices)

    def resolve(self, route: RouteRead) -> ResolvedPrice:
        # (1) selected airline on the route
        own = route.offer_for(self._airline)
        if own is not None:
            return ResolvedPrice(own.avg_price_eur, SRC_AIRLINE)

        # (2) other airlines on the route
        others = [o.avg_price_eur for o in route.offers if o.airline_iata != self._airline]
        if others:
            return ResolvedPrice(round(mean(others), 2), SRC_ROUTE_OTHERS)

        # (3) selected airline, similar distances in the same scope
        proxy = self._distance_proxy(route.distance_km)
        if proxy is not None:
            return ResolvedPrice(round(proxy, 2), SRC_DISTANCE_PROXY)

        # (final) scope-wide mean, or truly unavailable
        if self._scope_mean > 0:
            return ResolvedPrice(round(self._scope_mean, 2), SRC_SCOPE_MEAN)
        return ResolvedPrice(0.0, SRC_NONE)

    def _distance_proxy(self, distance_km: float) -> float | None:
        if not self._distances:
            return None
        low = distance_km * (1 - _SIMILAR_DISTANCE_BAND)
        high = distance_km * (1 + _SIMILAR_DISTANCE_BAND)
        lo = bisect_left(self._distances, low)
        band = [self._prices[i] for i in range(lo, len(self._distances)) if self._distances[i] <= high]
        if band:
            return mean(band)
        # No route in band: fall back to the nearest priced route by distance.
        nearest = min(range(len(self._distances)), key=lambda i: abs(self._distances[i] - distance_km))
        return self._prices[nearest]
