"""Read-through access to airport/airline master data with light caching.

The UI needs fast, repeated lookups (dropdown options, airport coordinates for
the map). This service memoises the (small) master-data tables in memory and
exposes convenience projections. It depends only on the ``CatalogRepository``
Protocol, not on SQLAlchemy.
"""

from __future__ import annotations

from functools import cached_property

from database.repository.interfaces import (
    AirlineRead,
    AirportRead,
    CatalogRepository,
)
from shared.constants import INTERCONTINENTAL


class CatalogService:
    def __init__(self, catalog_repo: CatalogRepository) -> None:
        self._repo = catalog_repo

    @cached_property
    def airports(self) -> list[AirportRead]:
        return self._repo.list_airports()

    @cached_property
    def airlines(self) -> list[AirlineRead]:
        return sorted(self._repo.list_airlines(), key=lambda a: a.name)

    @cached_property
    def airport_map(self) -> dict[str, AirportRead]:
        return {a.iata: a for a in self.airports}

    @cached_property
    def _airline_map(self) -> dict[str, AirlineRead]:
        return {a.iata: a for a in self.airlines}

    def airline(self, iata: str) -> AirlineRead | None:
        return self._airline_map.get(iata)

    def airport(self, iata: str) -> AirportRead | None:
        return self.airport_map.get(iata)

    def airline_options(self) -> list[tuple[str, str]]:
        """(iata, "IATA — Name") pairs for the airline dropdown."""
        return [(a.iata, f"{a.iata} — {a.name}") for a in self.airlines]

    def airports_for_scope(self, scope: str) -> list[AirportRead]:
        """Airports to display on the map for a scope (all for intercontinental)."""
        if scope == INTERCONTINENTAL:
            return self.airports
        return [a for a in self.airports if a.continent == scope]
