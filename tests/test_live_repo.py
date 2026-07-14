"""Integration tests for the live-data repositories over the temp DB.

Demand now flows through an injected provider's ``get_weekly_demand`` — the live
repo has no direct knowledge of demand internals.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from backend.dto import AnalysisRequest, FilterSettings
from backend.services.analysis_service import AnalysisService
from backend.services.catalog_service import CatalogService
from database.repository.observation_repo import (
    SqlAlchemyLiveRouteRepository,
    SqlAlchemyObservationRepository,
)
from shared.constants import Task

_WK = "2026-W27"
_SNAP = date(2026, 7, 6)


class _FakeDemand:
    """Stand-in demand provider returning a fixed value for AAA→BBB."""

    def get_weekly_demand(self, origin: str, destination: str, week: str):
        if origin == "AAA" and destination == "BBB":
            return SimpleNamespace(estimated_weekly_passengers=5000.0)
        return None


def _seed_supply(obs: SqlAlchemyObservationRepository) -> int:
    rid = obs.resolve_route_id("AAA", "BBB")  # both Europe in the seeded catalog
    obs.save_supply_snapshot([
        {"route_id": rid, "airline_iata": "LH", "week": _WK, "snapshot_date": _SNAP,
         "available_seats": 2000, "frequency": 10, "aircraft_type": "A320",
         "average_price": 150.0, "flight_number": None, "source": "airlabs"},
    ])
    return rid


def test_resolve_route_id_enriches_geography(seeded_repos):
    obs = SqlAlchemyObservationRepository()
    rid = obs.resolve_route_id("AAA", "CCC")  # Europe -> Asia
    assert obs.resolve_route_id("AAA", "CCC") == rid  # idempotent


def test_live_route_read_assembly(seeded_repos):
    obs = SqlAlchemyObservationRepository()
    live = SqlAlchemyLiveRouteRepository(demand_provider=_FakeDemand())
    rid = _seed_supply(obs)

    routes = live.routes_by_scope("Europe", _WK)
    match = [r for r in routes if r.id == rid]
    assert match, "route should appear in Europe scope"
    r = match[0]
    assert r.origin_iata == "AAA" and r.dest_iata == "BBB"
    assert r.total_demand == 5000.0        # supplied by the demand provider
    assert r.total_supply == 2000
    assert r.offers[0].airline_iata == "LH" and r.offers[0].seats_per_flight == 200

    assert rid in {x.id for x in live.routes_for_airline("LH", "Europe", _WK)}
    assert live.routes_for_airline("ZZ", "Europe", _WK) == []
    assert _WK in live.distinct_weeks()


def test_live_analysis_uses_unchanged_engine(seeded_repos):
    catalog_repo, _ = seeded_repos
    obs = SqlAlchemyObservationRepository()
    _seed_supply(obs)
    live = SqlAlchemyLiveRouteRepository(demand_provider=_FakeDemand())

    svc = AnalysisService(live, CatalogService(catalog_repo))
    resp = svc.analyze(
        AnalysisRequest(airline_iata="LH", scope="Europe", task=Task.OPPORTUNITIES,
                        filters=FilterSettings(), week=_WK)
    )
    assert resp.results
    assert all(r.benefit_eur >= 0 for r in resp.results)
