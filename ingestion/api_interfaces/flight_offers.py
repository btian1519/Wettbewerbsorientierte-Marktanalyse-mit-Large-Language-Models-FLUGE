"""Future flight-offer (supply) provider interface."""

from __future__ import annotations

from ingestion.interfaces import SupplyDemandBatch


class FlightOffersApi:
    """Supply-side provider (schedules / seat capacity) — not yet implemented.

    Implements the :class:`~ingestion.interfaces.SupplyDemandSource` Protocol so
    it can be dropped in wherever ``DemoDataSource`` is used today.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url

    def produce(self, week: str) -> SupplyDemandBatch:  # noqa: D401
        raise NotImplementedError(
            "FlightOffersApi is a prepared interface; live ingestion is not enabled yet."
        )
