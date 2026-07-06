"""Future demand-proxy provider interfaces (price comparison portals, trends)."""

from __future__ import annotations

from typing import Protocol


class DemandProxy(Protocol):
    """A demand signal keyed by directed route (origin_iata, dest_iata)."""

    def demand_index(self, week: str) -> dict[tuple[str, str], float]: ...


class PriceComparisonApi:
    """Demand proxy from price-comparison portals — not yet implemented."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def demand_index(self, week: str) -> dict[tuple[str, str], float]:
        raise NotImplementedError("PriceComparisonApi is a prepared interface only.")


class GoogleTrendsApi:
    """Demand proxy from Google Trends search interest — not yet implemented."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def demand_index(self, week: str) -> dict[tuple[str, str], float]:
        raise NotImplementedError("GoogleTrendsApi is a prepared interface only.")
