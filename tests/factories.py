"""Small builders for read-model test fixtures."""

from __future__ import annotations

from database.repository.interfaces import OfferRead, RouteRead


def offer(airline: str, capacity: int, price: float, seats: int = 180) -> OfferRead:
    freq = max(1, round(capacity / seats))
    return OfferRead(airline_iata=airline, seats_per_flight=seats, frequency=freq,
                     capacity=capacity, avg_price_eur=price)


def route(
    *,
    rid: int = 1,
    origin: str = "AAA",
    dest: str = "BBB",
    scope: str = "Europe",
    origin_cont: str = "Europe",
    dest_cont: str = "Europe",
    distance: float = 2000.0,
    demand: float = 1000.0,
    offers: tuple[OfferRead, ...] = (),
    week: str = "2026-W27",
) -> RouteRead:
    return RouteRead(
        id=rid, week=week, origin_iata=origin, dest_iata=dest,
        origin_continent=origin_cont, dest_continent=dest_cont, scope=scope,
        distance_km=distance, total_demand=demand, offers=offers,
    )
