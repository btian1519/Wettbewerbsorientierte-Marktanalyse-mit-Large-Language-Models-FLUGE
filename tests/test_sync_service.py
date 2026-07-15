"""The data-sync layer must cover the whole market, independent of UI state."""

from __future__ import annotations

import pytest

from backend.services.catalog_service import CatalogService
from database.repository.observation_repo import SqlAlchemyObservationRepository
from ingestion.connectors import AircraftDbConnector, AirLabsConnector, GoogleTrendsConnector
from ingestion.sync_service import SyncService
from shared.config import Settings
from shared.sources import DataSource
from tests.test_connectors import _Resp, _Session


@pytest.fixture(autouse=True)
def _clear_pauses(seeded_repos):
    """The seeded DB is session-scoped: a source paused by a rate/quota limit is
    persisted, so clear it around each test to keep supply syncs isolated."""
    repo = SqlAlchemyObservationRepository()
    repo.clear_sync_status("rate_limited")
    yield
    repo.clear_sync_status("rate_limited")


def _service(monkeypatch, catalog_repo) -> tuple[SyncService, _Session, SqlAlchemyObservationRepository]:
    monkeypatch.setenv("AIRLABS_API_KEY", "test-key")
    monkeypatch.delenv("SYNC_MAX_AIRPORTS", raising=False)
    settings = Settings()
    payload = {"response": [
        {"airline_iata": "LH", "dep_iata": "AAA", "arr_iata": "BBB", "days": ["mon", "tue"]},
    ]}
    session = _Session(_Resp(200, payload))
    connectors = {
        DataSource.AIRLABS: AirLabsConnector(settings, session=session),
        DataSource.GOOGLE_TRENDS: GoogleTrendsConnector(settings),
    }
    obs = SqlAlchemyObservationRepository()
    svc = SyncService(obs, CatalogService(catalog_repo), connectors, AircraftDbConnector(settings), settings)
    return svc, session, obs


def test_supply_sync_covers_full_market(seeded_repos, monkeypatch):
    catalog_repo, _ = seeded_repos
    svc, session, obs = _service(monkeypatch, catalog_repo)

    result = svc.sync_supply()

    # Every catalogued airport was crawled as a departure point — NOT just a
    # selected airline/continent. (Exclude the /ping probe, which has no dep_iata.)
    called = {params.get("dep_iata") for _url, params in session.calls if params.get("dep_iata")}
    catalog_iatas = {a.iata for a in CatalogService(catalog_repo).airports}
    assert called == catalog_iatas
    assert result.status == "success"
    assert result.coverage_scope == "Global"
    assert result.records >= 1

    # Coverage metadata recorded (data_source / coverage_scope / status / timestamp).
    cov = obs.coverage_for(DataSource.AIRLABS.value, "schedules")
    assert cov is not None
    assert cov["coverage_scope"] == "Global"
    assert cov["sync_status"] == "success"
    assert cov["sync_timestamp"] is not None


def test_sync_now_updates_supply_and_demand(seeded_repos, monkeypatch):
    catalog_repo, _ = seeded_repos
    svc, _session, obs = _service(monkeypatch, catalog_repo)

    results = svc.sync_market()
    categories = {r.category for r in results}
    assert "schedules" in categories and "demand" in categories

    # Both a supply and a demand coverage row exist afterwards.
    sources = {(c["data_source"], c["category"]) for c in obs.sync_states()}
    assert (DataSource.AIRLABS.value, "schedules") in sources
    assert (DataSource.GOOGLE_TRENDS.value, "demand") in sources


def test_quota_error_aborts_on_first_request(seeded_repos, monkeypatch):
    catalog_repo, _ = seeded_repos
    monkeypatch.setenv("AIRLABS_API_KEY", "test-key")
    monkeypatch.delenv("SYNC_MAX_AIRPORTS", raising=False)
    settings = Settings()
    payload = {"error": {"message": "The monthly request limit has been exceeded.", "code": "limit"}}
    session = _Session(_Resp(200, payload))
    connectors = {DataSource.AIRLABS: AirLabsConnector(settings, session=session)}
    svc = SyncService(
        SqlAlchemyObservationRepository(), CatalogService(catalog_repo),
        connectors, AircraftDbConnector(settings), settings,
    )

    result = svc.sync_supply()
    # A provider usage limit now pauses the source (persisted), rather than a
    # generic error, so future syncs skip it instead of hammering the quota.
    assert result.status == "rate_limited"
    assert "monthly request limit" in result.error
    # Aborted on the first airport — did not burn the circuit-breaker's 5 requests.
    dep_calls = [p for _u, p in session.calls if p.get("dep_iata")]
    assert len(dep_calls) == 1


def test_max_airports_cap_makes_coverage_partial(seeded_repos, monkeypatch):
    catalog_repo, _ = seeded_repos
    svc, session, _obs = _service(monkeypatch, catalog_repo)  # helper clears the cap
    monkeypatch.setenv("SYNC_MAX_AIRPORTS", "2")
    svc._settings = Settings()  # now reads cap = 2

    result = svc.sync_supply()
    called = {params.get("dep_iata") for _url, params in session.calls if params.get("dep_iata")}
    assert len(called) == 2
    assert result.coverage_scope.startswith("Partial")
