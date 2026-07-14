"""Vocabulary for external data sources and sync categories.

Shared by the ORM models, the connectors and the scheduler so everyone agrees on
the same string identifiers (portable across SQLite/PostgreSQL — stored as text).
"""

from __future__ import annotations

from enum import Enum


class DataSource(str, Enum):
    """Origin of a stored observation."""

    DEMO = "demo"
    AIRLABS = "airlabs"
    OPENSKY = "opensky"
    EUROSTAT = "eurostat"
    AMADEUS = "amadeus"
    GOOGLE_TRENDS = "google_trends"
    WIKIPEDIA = "wikipedia"
    WORLDBANK = "worldbank"
    OPENFLIGHTS = "openflights"
    AIRCRAFT_DB = "aircraft_db"
    COMPUTED = "computed"  # derived values (e.g. demand engine output)


class SyncCategory(str, Enum):
    """What a scheduled sync job refreshes (drives the update frequency)."""

    AIRPORT_METADATA = "airport_metadata"
    SCHEDULES = "schedules"
    PRICES = "prices"
    DEMAND = "demand"
    VALIDATION = "validation"


# The "live" (non-demo) data sources, in a sensible display order.
LIVE_SOURCES: tuple[DataSource, ...] = (
    DataSource.AIRLABS,
    DataSource.OPENSKY,
    DataSource.EUROSTAT,
    DataSource.AMADEUS,
    DataSource.GOOGLE_TRENDS,
)
