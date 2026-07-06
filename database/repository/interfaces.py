"""Repository contracts + neutral read-models.

Read-models are plain frozen dataclasses (no ORM, no live session) so the
analysis engine can consume query results freely without worrying about lazy
loading or session scope. The ``Protocol`` classes define the seams that the
backend services depend on — enabling dependency injection and test doubles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


# --------------------------------------------------------------------------- #
# Read models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AirportRead:
    iata: str
    name: str | None
    country: str | None
    lon: float
    lat: float
    continent: str


@dataclass(frozen=True, slots=True)
class AirlineRead:
    iata: str
    name: str
    base: str
    region: str
    base_iata: str | None


@dataclass(frozen=True, slots=True)
class OfferRead:
    airline_iata: str
    seats_per_flight: int
    frequency: int
    capacity: int
    avg_price_eur: float


@dataclass(frozen=True, slots=True)
class RouteRead:
    id: int
    week: str
    origin_iata: str
    dest_iata: str
    origin_continent: str
    dest_continent: str
    scope: str
    distance_km: float
    total_demand: float
    offers: tuple[OfferRead, ...]

    @property
    def total_supply(self) -> int:
        return sum(o.capacity for o in self.offers)

    @property
    def num_airlines(self) -> int:
        return len(self.offers)

    def offer_for(self, airline_iata: str) -> OfferRead | None:
        for o in self.offers:
            if o.airline_iata == airline_iata:
                return o
        return None


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #
class CatalogRepository(Protocol):
    """Master data (airports & airlines)."""

    def replace_airports(self, rows: Sequence[dict]) -> None: ...
    def replace_airlines(self, rows: Sequence[dict]) -> None: ...
    def list_airports(self) -> list[AirportRead]: ...
    def list_airlines(self) -> list[AirlineRead]: ...
    def airport_count(self) -> int: ...
    def airline_count(self) -> int: ...


class RouteRepository(Protocol):
    """Weekly supply/demand facts."""

    def bulk_load(self, route_rows: Sequence[dict], offer_rows: Sequence[dict]) -> None: ...
    def clear_routes(self) -> None: ...
    def route_count(self, week: str | None = None) -> int: ...
    def offer_count(self) -> int: ...
    def distinct_weeks(self) -> list[str]: ...
    def routes_by_scope(self, scope: str, week: str) -> list[RouteRead]: ...
    def routes_for_airline(self, airline_iata: str, scope: str, week: str) -> list[RouteRead]: ...
    def route_count_by_scope(self, week: str) -> dict[str, int]: ...
