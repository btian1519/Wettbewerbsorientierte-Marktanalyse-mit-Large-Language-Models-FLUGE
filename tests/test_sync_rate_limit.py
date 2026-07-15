"""Rate-limit circuit breaker: a source that returns 429/quota is paused,
the pause persists (survives restarts via SyncState) and is shown as such."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services.catalog_service import CatalogService
from backend.services.demand_service import DemandService
from database.repository.demand_repo import SqlAlchemyDemandRepository
from database.repository.observation_repo import SqlAlchemyObservationRepository
from frontend.sidebar import diagnostics as dg
from ingestion.connectors.base import BaseConnector, ConnectorError
from ingestion.demand.records import RouteContext
from ingestion.demand.wikipedia_connector import WikipediaDemandConnector
from ingestion.sync_service import SyncResult, SyncService, _looks_rate_limited
from shared.config import Settings, get_settings
from shared.sources import DataSource
from tests.test_connectors import _Resp, _Session


@pytest.fixture(autouse=True)
def _clear_pauses(seeded_repos):
    """The seeded DB is session-scoped; never let a persisted pause leak between
    tests (a stray ``rate_limited`` state would make later syncs skip)."""
    repo = SqlAlchemyObservationRepository()
    repo.clear_sync_status("rate_limited")
    yield
    repo.clear_sync_status("rate_limited")


def _svc(repo: SqlAlchemyObservationRepository) -> SyncService:
    # Only the repo is exercised on the pause/skip/finalize paths.
    return SyncService(repo, catalog_service=None, connectors={}, aircraft_db=None,
                       settings=get_settings(), demand_service=None)


# --------------------------------------------------------------------------- #
# Pure detection
# --------------------------------------------------------------------------- #
def test_looks_rate_limited():
    assert _looks_rate_limited("airlabs: HTTP 429")
    assert _looks_rate_limited("Request quota exceeded")
    assert _looks_rate_limited("Too Many Requests")
    assert not _looks_rate_limited("HTTP 500 server error")
    assert not _looks_rate_limited(None)


# --------------------------------------------------------------------------- #
# A 429 result is classified + persisted as rate_limited
# --------------------------------------------------------------------------- #
def test_finalize_marks_and_persists_rate_limited(seeded_repos):
    repo = SqlAlchemyObservationRepository()
    svc = _svc(repo)
    r = SyncResult("airlabs", "schedules", "error", coverage_scope="Global", error="airlabs: HTTP 429")
    svc._finalize(r)
    assert r.status == "rate_limited"
    assert repo.coverage_for("airlabs", "schedules")["sync_status"] == "rate_limited"


# --------------------------------------------------------------------------- #
# Once paused, the source is skipped without touching connectors, and the
# persisted pause is preserved (so it is still the default next start).
# --------------------------------------------------------------------------- #
def test_paused_source_is_skipped_and_stays_paused(seeded_repos):
    repo = SqlAlchemyObservationRepository()
    repo.upsert_sync_state("airlabs", "schedules", "Global", "rate_limited", 0)
    svc = _svc(repo)  # empty connectors: if it did NOT skip, it would fail differently
    res = svc.sync_supply()
    assert res.status == "skipped"
    assert "paused" in (res.error or "").lower()
    # The pause is preserved (not overwritten by the skip) -> default at next start.
    assert repo.coverage_for("airlabs", "schedules")["sync_status"] == "rate_limited"


# --------------------------------------------------------------------------- #
# Explicit resume clears the persisted pause.
# --------------------------------------------------------------------------- #
def test_resume_clears_pause(seeded_repos):
    repo = SqlAlchemyObservationRepository()
    repo.upsert_sync_state("airlabs", "schedules", "Global", "rate_limited", 0)
    svc = _svc(repo)
    assert svc.resume_paused_sources() >= 1
    assert repo.coverage_for("airlabs", "schedules")["sync_status"] != "rate_limited"


def test_status_lists_paused_sources(seeded_repos):
    repo = SqlAlchemyObservationRepository()
    repo.upsert_sync_state("airlabs", "schedules", "Global", "rate_limited", 0)
    svc = _svc(repo)
    assert "airlabs" in svc.status()["paused_sources"]


# --------------------------------------------------------------------------- #
# Display reflects the paused state.
# --------------------------------------------------------------------------- #
def test_display_shows_rate_limited():
    snap = {"sync": {"connectors": {"airlabs": "unknown"}, "recent_runs": [],
                     "paused_sources": ["airlabs"]}}
    card = dg.source_statuses(snap)[0]
    assert card["emoji"] == "🟡"
    assert card["headline"] == "Rate limited"


def test_wikipedia_featured_as_external_source():
    # Wikipedia is a demand connector; its availability arrives via demand.source_states.
    snap = {
        "sync": {"connectors": {}, "recent_runs": [], "paused_sources": []},
        "demand": {"source_states": {"wikipedia": "available"}},
    }
    cards = {c["name"]: c for c in dg.source_statuses(snap)}
    assert "Wikipedia" in cards
    assert cards["Wikipedia"]["emoji"] == "🟢"
    assert cards["Wikipedia"]["headline"] == "Available"


def test_wikipedia_shows_paused_when_rate_limited():
    snap = {
        "sync": {"connectors": {}, "recent_runs": [], "paused_sources": ["wikipedia"]},
        "demand": {"source_states": {"wikipedia": "available"}},
    }
    cards = {c["name"]: c for c in dg.source_statuses(snap)}
    assert cards["Wikipedia"]["emoji"] == "🟡"
    assert cards["Wikipedia"]["headline"] == "Rate limited"


def test_summarize_rate_limited_result():
    r = SimpleNamespace(source="airlabs", status="rate_limited", error="airlabs: HTTP 429", records=0)
    icon, msg = dg.summarize_sync_result(r)
    assert "paused" in msg.lower()


# --------------------------------------------------------------------------- #
# Demand pipeline: a connector that 429s is stopped within the run AND persisted,
# so it is not hammered once per O-D pair (the reported bug).
# --------------------------------------------------------------------------- #
class _RateLimited429:
    source = DataSource.GOOGLE_TRENDS
    signal_type = "google_trends"

    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return True

    def fetch(self, ctx, week):
        self.calls += 1
        raise ConnectorError("google_trends: The request failed: Google returned a response with code 429")


def _demand_service(catalog_repo, connector) -> DemandService:
    return DemandService(
        SqlAlchemyDemandRepository(),
        SqlAlchemyObservationRepository(),
        CatalogService(catalog_repo),
        [connector],
        settings=get_settings(),
    )


def _contexts(n: int) -> list[RouteContext]:
    return [RouteContext(origin_iata=f"O{i:02d}", dest_iata=f"D{i:02d}",
                         origin_city=None, dest_city=None) for i in range(n)]


def test_demand_connector_stops_after_first_429(seeded_repos):
    catalog_repo, _ = seeded_repos
    conn = _RateLimited429()
    svc = _demand_service(catalog_repo, conn)

    svc.sync(route_contexts=_contexts(5))
    # Called ONCE, not once per O-D pair — the breaker disabled it after the 429.
    assert conn.calls == 1
    # ...and the pause is persisted for future runs (survives restarts).
    repo = SqlAlchemyObservationRepository()
    state = repo.coverage_for("google_trends", "demand_signal")
    assert state is not None and state["sync_status"] == "rate_limited"


def test_demand_paused_connector_skipped_next_run(seeded_repos):
    catalog_repo, _ = seeded_repos
    SqlAlchemyObservationRepository().upsert_sync_state(
        "google_trends", "demand_signal", "Global", "rate_limited", 0
    )
    conn = _RateLimited429()
    svc = _demand_service(catalog_repo, conn)

    svc.sync(route_contexts=_contexts(5))
    # Already paused from the start → never called this run.
    assert conn.calls == 0


class _Failing404:
    """A connector that systematically fails without being a rate limit."""

    source = DataSource.WIKIPEDIA
    signal_type = "wikipedia_views"

    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return True

    def fetch(self, ctx, week):
        self.calls += 1
        raise ConnectorError('wikipedia: HTTP 404 — no data for those dates')


def test_demand_connector_stops_after_repeated_failures(seeded_repos):
    from backend.services.demand_service import _DEMAND_FAILURE_LIMIT

    catalog_repo, _ = seeded_repos
    conn = _Failing404()
    svc = _demand_service(catalog_repo, conn)

    svc.sync(route_contexts=_contexts(20))
    # Stops after N consecutive failures instead of firing once per O-D pair.
    assert conn.calls == _DEMAND_FAILURE_LIMIT
    # ...and the pause is persisted (survives restart, default paused next start).
    state = SqlAlchemyObservationRepository().coverage_for("wikipedia", "demand_signal")
    assert state is not None and state["sync_status"] == "rate_limited"


# --------------------------------------------------------------------------- #
# Connector-level breaker: stops the HTTP + log storm even when the connector
# swallows individual request failures (the reported Wikipedia HTTP 404 case).
# --------------------------------------------------------------------------- #
class _NotFoundConnector(BaseConnector):
    source = DataSource.WIKIPEDIA
    base_url = "https://example.test"
    circuit_breaker_threshold = 2


def test_connector_circuit_opens_and_stops_calling_network():
    session = _Session(_Resp(404, {"detail": "no data for those dates"}))
    c = _NotFoundConnector(Settings(), session=session)

    for _ in range(2):  # two real failures open the circuit
        with pytest.raises(ConnectorError):
            c._get("some/path")
    assert c.is_circuit_open()
    calls_when_opened = len(session.calls)

    # Further requests fail fast WITHOUT touching the network.
    for _ in range(5):
        with pytest.raises(ConnectorError):
            c._get("some/path")
    assert len(session.calls) == calls_when_opened

    c.reset_circuit()
    assert not c.is_circuit_open()


def test_demand_swallowing_connector_stops_hammering(seeded_repos):
    from backend.services.demand_service import _DEMAND_FAILURE_LIMIT

    catalog_repo, _ = seeded_repos
    session = _Session(_Resp(404, {"detail": "no data for those dates"}))
    conn = WikipediaDemandConnector(Settings(), session=session)  # fetch() swallows 404s -> []
    svc = _demand_service(catalog_repo, conn)

    ctxs = [RouteContext(origin_iata=f"O{i:02d}", dest_iata=f"D{i:02d}",
                         origin_city=f"City{i}", dest_city=f"Dest{i}") for i in range(20)]
    svc.sync(route_contexts=ctxs)
    # Despite 20 routes, the network was hit only until the breaker opened...
    assert len(session.calls) == _DEMAND_FAILURE_LIMIT
    # ...and the source is paused persistently (shown as "Rate limited", survives
    # restart) even though fetch() swallowed each individual 404.
    state = SqlAlchemyObservationRepository().coverage_for("wikipedia", "demand_signal")
    assert state is not None and state["sync_status"] == "rate_limited"
