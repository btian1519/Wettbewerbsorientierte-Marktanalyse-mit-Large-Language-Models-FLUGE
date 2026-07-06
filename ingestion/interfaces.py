"""Ingestion contracts.

These Protocols are the extension points for future data sources. A new provider
(e.g. a flight-offer API or a Google-Trends demand proxy) only has to implement
the relevant Protocol and be registered in the ingestion service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class SupplyDemandBatch:
    """A batch of weekly route facts ready for bulk persistence.

    ``route_rows`` and ``offer_rows`` are dict payloads matching the ORM columns
    of :class:`~database.models.route.RouteWeek` and
    :class:`~database.models.route.AirlineOffer` respectively. Offers reference
    routes via the explicit ``route_week_id`` assigned by the producer.
    """

    week: str
    route_rows: Sequence[dict]
    offer_rows: Sequence[dict]


class MasterDataSource(Protocol):
    """Provides airport / airline master data."""

    def load_airports(self) -> list[dict]: ...
    def load_airlines(self) -> list[dict]: ...


class SupplyDemandSource(Protocol):
    """Provides weekly supply/demand facts for routes."""

    def produce(self, week: str) -> SupplyDemandBatch: ...
