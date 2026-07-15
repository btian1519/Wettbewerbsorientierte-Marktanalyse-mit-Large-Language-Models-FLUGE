"""The benefit / delta model — the analytical heart of FlightScope AI.

Formula (per directed route, per week):

    delta          = demand - total_supply
    x              = Network Availability slider / 100          (0..1)
    net_factor F   = 0.5 * (1 + sign(delta) * (2*x - 1))
    distance_eff   = clamp(1 - |distance - 2000| / 10000, 0, 1)
    marge_proxy    = 0.5 * net_factor + 0.5 * distance_eff
    benefit_full   = delta * marge_proxy * marge_average * price_eur

``net_factor`` (F) makes the same slider act *mirror-symmetrically* on market gaps
(delta > 0) and overcapacities (delta < 0); at delta = 0 it is a neutral 0.5.
See :func:`network_availability_factor`.

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


def _sign(value: float) -> float:
    """Mathematical sign: +1 if value > 0, -1 if value < 0, 0 if value == 0."""
    if value > 0:
        return 1.0
    if value < 0:
        return -1.0
    return 0.0


def network_availability_factor(slider_value: float, delta: float) -> float:
    """Direction-dependent Network Availability factor ``F``.

    ``slider_value`` is the slider already converted to ``x = r / 100`` (0..1). The
    factor actually used in the benefit formula depends on the sign of the market
    delta ``Z = demand - supply``::

        F = 0.5 * (1 + sign(Z) * (2*x - 1))

    So a market gap (Z > 0) and an overcapacity (Z < 0) react mirror-symmetrically
    to the same slider position (e.g. x=1.0 gives F=1.0 for a gap but F=0.0 for an
    overcapacity), and Z = 0 always yields a neutral ``F = 0.5``.
    """
    return 0.5 * (1.0 + _sign(delta) * (2.0 * slider_value - 1.0))


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
        # Network Availability is applied direction-dependently: the stored value is
        # the slider fraction x; F depends on the sign of this route's market delta.
        network_factor = network_availability_factor(filters.network_availability, delta_full)
        proxy = marge_proxy(network_factor, route.distance_km)
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
