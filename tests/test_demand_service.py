"""Demand service: pipeline round-trip and the get_weekly_demand contract."""

from __future__ import annotations

from backend.services.catalog_service import CatalogService
from backend.services.demand_service import DemandService
from database.repository.demand_repo import SqlAlchemyDemandRepository
from database.repository.observation_repo import SqlAlchemyObservationRepository
from ingestion.demand.records import RawSignal
from shared.config import Settings

_WK = "2026-W27"


def _service(catalog_repo) -> tuple[DemandService, SqlAlchemyObservationRepository, SqlAlchemyDemandRepository]:
    demand_repo = SqlAlchemyDemandRepository()
    obs = SqlAlchemyObservationRepository()
    svc = DemandService(demand_repo, obs, CatalogService(catalog_repo), connectors=[], settings=Settings())
    return svc, obs, demand_repo


def _signals() -> list[RawSignal]:
    return [
        RawSignal(origin_airport="AAA", destination_airport="BBB", signal_type="google_trends",
                  signal_value=90, source="google_trends"),
        RawSignal(origin_airport="AAA", destination_airport="BBB", signal_type="wikipedia_views",
                  signal_value=8000, source="wikipedia"),
        RawSignal(origin_airport="CCC", destination_airport="AAA", signal_type="google_trends",
                  signal_value=30, source="google_trends"),
    ]


def test_compute_and_get_weekly_demand(seeded_repos):
    catalog_repo, _ = seeded_repos
    svc, _obs, demand_repo = _service(catalog_repo)

    n = svc.compute_from_signals(_signals(), week=_WK)
    assert n == 2  # two distinct routes

    wd = svc.get_weekly_demand("AAA", "BBB", _WK)
    assert wd is not None
    assert wd.estimated_weekly_passengers > 0
    assert 0.0 <= wd.confidence_score <= 1.0
    assert wd.demand_index > 0

    # Unknown route -> None (the engine sees no demand rather than a guess).
    assert svc.get_weekly_demand("BBB", "CCC", _WK) is None

    # Raw signals were persisted for later trend/ML use.
    assert demand_repo.status()["signals"] == 3


class _FakeConn:
    signal_type = "google_trends"

    def available(self) -> bool:
        return True

    def fetch(self, ctx, week):
        return [RawSignal(origin_airport=ctx.origin_iata, destination_airport=ctx.dest_iata,
                          signal_type="google_trends", signal_value=50.0, source="google_trends")]


def test_demand_universe_independent_of_supply(seeded_repos):
    catalog_repo, _ = seeded_repos
    svc, _obs, _repo = _service(catalog_repo)

    # Route universe is generated from the AIRPORTS catalog (AAA/BBB/CCC = 6
    # ordered pairs), NOT from supply-discovered routes.
    ctxs = svc._market_route_contexts()
    assert len(ctxs) == 6
    assert {c.origin_iata for c in ctxs} | {c.dest_iata for c in ctxs} == {"AAA", "BBB", "CCC"}


def test_demand_sync_runs_without_any_supply(seeded_repos):
    catalog_repo, _ = seeded_repos
    demand_repo = SqlAlchemyDemandRepository()
    obs = SqlAlchemyObservationRepository()
    svc = DemandService(demand_repo, obs, CatalogService(catalog_repo), connectors=[_FakeConn()], settings=Settings())

    result = svc.sync(week="2026-W27")  # no supply data required
    assert result.status == "success"
    assert result.normalized > 0
    assert svc.get_weekly_demand("AAA", "BBB", "2026-W27") is not None


def test_calibration_path_raises_confidence(seeded_repos):
    catalog_repo, _ = seeded_repos
    svc, obs, demand_repo = _service(catalog_repo)

    # Fallback estimate first (no reference).
    svc.compute_from_signals(_signals(), week=_WK)
    fallback = svc.get_weekly_demand("AAA", "BBB", _WK)

    # Provide a reference calibration, recompute.
    rid = obs.resolve_route_id("AAA", "BBB")
    demand_repo.save_calibration([{
        "route_id": rid, "reference_passengers": 12000.0,
        "reference_source": "eurostat", "calibration_factor": 130.0,
    }])
    svc.compute_from_signals(_signals(), week=_WK)
    calibrated = svc.get_weekly_demand("AAA", "BBB", _WK)

    assert calibrated.confidence_score > fallback.confidence_score
    # estimate == demand_index * calibration_factor
    assert abs(calibrated.estimated_weekly_passengers - calibrated.demand_index * 130.0) < 1.0
