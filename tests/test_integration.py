"""Integration tests over a temp SQLite DB (see conftest.seeded_repos)."""

from __future__ import annotations

from backend.dto import AnalysisRequest, FilterSettings
from backend.services.analysis_service import AnalysisService
from backend.services.catalog_service import CatalogService
from shared.constants import Task


def test_repository_scope_queries(seeded_repos):
    _catalog, routes = seeded_repos
    europe = routes.routes_by_scope("Europe", "2026-W27")
    assert {r.id for r in europe} == {1, 2}
    inter = routes.routes_by_scope("Global/Intercontinental", "2026-W27")
    assert {r.id for r in inter} == {3}
    # total supply aggregation on route 1 = 2000 + 1000
    r1 = next(r for r in europe if r.id == 1)
    assert r1.total_supply == 3000


def test_routes_for_airline_filters_to_operator(seeded_repos):
    _catalog, routes = seeded_repos
    lh_eu = routes.routes_for_airline("LH", "Europe", "2026-W27")
    assert {r.id for r in lh_eu} == {1}  # LH only operates route 1 in Europe
    af_eu = routes.routes_for_airline("AF", "Europe", "2026-W27")
    assert {r.id for r in af_eu} == {1}


def test_opportunities_surface_unserved_route(seeded_repos):
    catalog_repo, route_repo = seeded_repos
    svc = AnalysisService(route_repo, CatalogService(catalog_repo))
    resp = svc.analyze(
        AnalysisRequest(airline_iata="LH", scope="Europe", task=Task.OPPORTUNITIES, filters=FilterSettings())
    )
    # Route 2 (unserved, demand 5000) must outrank the oversupplied route 1.
    assert resp.results[0].origin_iata == "BBB"
    assert resp.results[0].dest_iata == "AAA"
    assert resp.results[0].benefit_eur > 0


def test_opportunities_exclude_negative_benefit(seeded_repos):
    catalog_repo, route_repo = seeded_repos
    svc = AnalysisService(route_repo, CatalogService(catalog_repo))
    resp = svc.analyze(
        AnalysisRequest(airline_iata="LH", scope="Europe", task=Task.OPPORTUNITIES, filters=FilterSettings())
    )
    # Every opportunity has non-negative benefit ...
    assert all(r.benefit_eur >= 0 for r in resp.results)
    # ... and the oversupplied route 1 (AAA->BBB, supply 3000 > demand 1000) is gone.
    assert all(not (r.origin_iata == "AAA" and r.dest_iata == "BBB") for r in resp.results)


def test_overcapacities_only_airline_routes_and_negative(seeded_repos):
    catalog_repo, route_repo = seeded_repos
    svc = AnalysisService(route_repo, CatalogService(catalog_repo))
    resp = svc.analyze(
        AnalysisRequest(airline_iata="LH", scope="Europe", task=Task.OVERCAPACITIES, filters=FilterSettings())
    )
    assert len(resp.results) == 1  # LH operates only route 1 in Europe
    top = resp.results[0]
    assert top.benefit_eur < 0            # oversupply => negative benefit
    assert 0 < top.selected_airline_share <= 1
    assert top.gap_label == "Overcapacities"
