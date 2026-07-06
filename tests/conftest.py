"""Pytest fixtures.

A throwaway on-disk SQLite database is configured *before* any settings/engine
caches are populated, so integration tests never touch the real demo database.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Point the whole app at a temp DB before anything imports/caches the engine.
_TMP_DB = Path(tempfile.gettempdir()) / "flightscope_test.db"
os.environ["FLIGHTSCOPE_DB_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["FLIGHTSCOPE_LOG_LEVEL"] = "WARNING"


@pytest.fixture(scope="session")
def seeded_repos():
    """Fresh schema + a tiny hand-built dataset in the temp DB."""
    from database.migrations import reset_schema
    from database.repository.sqlalchemy_repo import (
        SqlAlchemyCatalogRepository,
        SqlAlchemyRouteRepository,
    )

    reset_schema()
    catalog = SqlAlchemyCatalogRepository()
    routes = SqlAlchemyRouteRepository()

    catalog.replace_airports(
        [
            {"iata": "AAA", "name": "Alpha", "country": "DE", "lon": 8.0, "lat": 50.0, "continent": "Europe"},
            {"iata": "BBB", "name": "Bravo", "country": "FR", "lon": 2.0, "lat": 48.0, "continent": "Europe"},
            {"iata": "CCC", "name": "Charlie", "country": "JP", "lon": 139.0, "lat": 35.0, "continent": "Asia"},
        ]
    )
    catalog.replace_airlines(
        [
            {"iata": "LH", "name": "Lufthansa", "base": "Munich (MUC)", "region": "Europe", "base_iata": "MUC"},
            {"iata": "AF", "name": "Air France", "base": "Paris (CDG)", "region": "Europe", "base_iata": "CDG"},
        ]
    )

    route_rows = [
        # Served Europe route with overcapacity (supply 3000 > demand 1000)
        {"id": 1, "week": "2026-W27", "origin_iata": "AAA", "dest_iata": "BBB",
         "origin_continent": "Europe", "dest_continent": "Europe", "scope": "Europe",
         "distance_km": 2000.0, "total_demand": 1000.0},
        # Unserved Europe route with demand (opportunity)
        {"id": 2, "week": "2026-W27", "origin_iata": "BBB", "dest_iata": "AAA",
         "origin_continent": "Europe", "dest_continent": "Europe", "scope": "Europe",
         "distance_km": 2000.0, "total_demand": 5000.0},
        # Intercontinental route
        {"id": 3, "week": "2026-W27", "origin_iata": "AAA", "dest_iata": "CCC",
         "origin_continent": "Europe", "dest_continent": "Asia", "scope": "Global/Intercontinental",
         "distance_km": 9000.0, "total_demand": 2000.0},
    ]
    offer_rows = [
        {"id": 1, "route_week_id": 1, "airline_iata": "LH", "seats_per_flight": 200,
         "frequency": 10, "capacity": 2000, "avg_price_eur": 150.0},
        {"id": 2, "route_week_id": 1, "airline_iata": "AF", "seats_per_flight": 200,
         "frequency": 5, "capacity": 1000, "avg_price_eur": 170.0},
        {"id": 3, "route_week_id": 3, "airline_iata": "LH", "seats_per_flight": 300,
         "frequency": 7, "capacity": 2100, "avg_price_eur": 700.0},
    ]
    routes.bulk_load(route_rows, offer_rows)
    return catalog, routes
