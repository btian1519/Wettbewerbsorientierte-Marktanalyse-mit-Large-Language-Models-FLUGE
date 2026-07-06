"""Placeholder interfaces for future live-data providers.

No network calls are implemented yet — these classes fix the *shape* of future
integrations so that wiring them in later is a registration change only. Each
raises :class:`NotImplementedError` to make the "not yet available" state loud.
"""

from ingestion.api_interfaces.flight_offers import FlightOffersApi
from ingestion.api_interfaces.demand_proxies import GoogleTrendsApi, PriceComparisonApi

__all__ = ["FlightOffersApi", "GoogleTrendsApi", "PriceComparisonApi"]
