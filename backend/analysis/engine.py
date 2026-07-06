"""The benefit / delta model — the analytical heart of FlightScope AI.

Formula (per directed route, per week):

    delta          = demand - total_supply
    distance_eff   = clamp(1 - |distance - 2000| / 10000, 0, 1)
    marge_proxy    = 0.5 * network_availability + 0.5 * distance_eff
    benefit_full   = delta * marge_proxy * marge_average * price_eur

For **overcapacities**, benefit and delta are reduced to the selected airline's
*proportional* share of supply (``airline_capacity / total_supply``), because the
question there is "how much of this oversupply is mine to cut?". For
**opportunities** the full route figures are used (an entrant would capture the
gap), while the share is still reported for context.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.dto import FilterSettings
from database.repository.interfaces import RouteRead
from shared.constants import (
    DISTANCE_EFFICIENCY_PEAK_KM,
    DISTANCE_EFFICIENCY_SPREAD_KM,
    Task,
)
from shared.utils import clamp


def distance_efficiency(distance_km: float) -> float:
    """Efficiency peaks at the reference stage length and decays with deviation."""
    raw = 1.0 - abs(distance_km - DISTANCE_EFFICIENCY_PEAK_KM) / DISTANCE_EFFICIENCY_SPREAD_KM
    return clamp(raw, 0.0, 1.0)


def marge_proxy(network_availability: float, distance_km: float) -> float:
    return 0.5 * network_availability + 0.5 * distance_efficiency(distance_km)


@dataclass(frozen=True, slots=True)
class ScoredRoute:
    """A route with its computed economics, ready for ranking."""

    route: RouteRead
    price_eur: float
    price_source: str
    delta_pax: float          # mode-adjusted (airline share for overcapacity)
    benefit_eur: float        # mode-adjusted
    airline_share: float      # selected airline supply share (0..1)


class BenefitEngine:
    """Stateless computation of route economics for a given task/filters."""

    def score(
        self,
        route: RouteRead,
        price_eur: float,
        price_source: str,
        filters: FilterSettings,
        task: Task,
        airline_iata: str,
    ) -> ScoredRoute:
        total_supply = route.total_supply
        delta_full = route.total_demand - total_supply
        proxy = marge_proxy(filters.network_availability, route.distance_km)
        benefit_full = delta_full * proxy * filters.marge_average * price_eur

        offer = route.offer_for(airline_iata)
        share = (offer.capacity / total_supply) if (offer and total_supply > 0) else 0.0

        if task == Task.OVERCAPACITIES:
            delta = delta_full * share
            benefit = benefit_full * share
        else:
            delta = delta_full
            benefit = benefit_full

        return ScoredRoute(
            route=route,
            price_eur=price_eur,
            price_source=price_source,
            delta_pax=delta,
            benefit_eur=benefit,
            airline_share=share,
        )
