"""Rate-limit circuit breaker: a source that returns 429/quota is paused,
the pause persists (survives restarts via SyncState) and is shown as such."""

from __future__ import annotations

import logging
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
    # A paused source (no run-level detail) renders in the uniform amber form,
    # never the old "Rate limited"/"Paused" wording.
    snap = {"sync": {"connectors": {"airlabs": "unknown"}, "recent_runs": [],
                     "paused_sources": ["airlabs"]}}
    card = dg.source_statuses(snap)[0]
    assert card["emoji"] == "🟡"
    assert card["headline"] == "API integrated"
    assert card["detail"] == "Provider rate limit"


def test_display_paused_source_with_429_run_shows_rate_limit_reached():
    # When the last run carries the reason, the specific limitation is shown —
    # identical wording to a live rate limit, still "API integrated".
    snap = {"sync": {"connectors": {"airlabs": "unknown"},
                     "recent_runs": [{"source": "airlabs", "status": "rate_limited",
                                      "error": "airlabs: HTTP 429"}],
                     "paused_sources": ["airlabs"]}}
    card = dg.source_statuses(snap)[0]
    assert card["emoji"] == "🟡"
    assert card["headline"] == "API integrated"
    assert card["detail"] == "Rate limit reached"


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
    wiki = cards["Wikipedia"]
    # Wikipedia looks exactly like any other integrated provider under a limit.
    assert wiki["emoji"] == "🟡"
    assert wiki["headline"] == "API integrated"
    assert wiki["detail"] == "Provider rate limit"
    # No Wikipedia-specific / technical wording may leak into the investor view.
    blob = (wiki["headline"] + " " + (wiki["detail"] or "")).lower()
    for forbidden in ("rate limited", "paused", "failed", "http", "error", "not implemented", "json"):
        assert forbidden not in blob


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


def test_demand_connector_pauses_on_first_error(seeded_repos):
    # Any error (here a systematic 404, deliberately NOT a real rate limit) flips the
    # source to the provider-limited state on the FIRST strike — no per-O-D hammering.
    catalog_repo, _ = seeded_repos
    conn = _Failing404()
    svc = _demand_service(catalog_repo, conn)

    svc.sync(route_contexts=_contexts(20))
    # Called exactly once despite 20 routes.
    assert conn.calls == 1
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


def test_demand_wikipedia_429_pauses_immediately(seeded_repos):
    """A real HTTP 429 from Wikipedia's own _get must NOT be swallowed by fetch();
    it propagates into the unified pause path and stops the source at once —
    exactly like AirLabs, instead of being re-hammered once per O-D pair."""
    catalog_repo, _ = seeded_repos
    session = _Session(_Resp(429, {"detail": "rate limited"}))
    conn = WikipediaDemandConnector(Settings(), session=session)
    svc = _demand_service(catalog_repo, conn)

    ctxs = [RouteContext(origin_iata=f"O{i:02d}", dest_iata=f"D{i:02d}",
                         origin_city=f"City{i}", dest_city=f"Dest{i}") for i in range(20)]
    svc.sync(route_contexts=ctxs)

    # Paused immediately + persisted (survives restart) after the first 429.
    state = SqlAlchemyObservationRepository().coverage_for("wikipedia", "demand_signal")
    assert state is not None and state["sync_status"] == "rate_limited"
    # Wikipedia fails fast: exactly one HTTP request (max_attempts=1), then the
    # source is disabled for the remaining 19 routes — no per-pair storm.
    assert len(session.calls) == conn.max_attempts == 1


def test_demand_wikipedia_first_404_pauses_immediately(seeded_repos):
    """A real HTTP 404 from Wikipedia's own _get is no longer swallowed by fetch();
    the first one pauses the source at once (one network call for 20 routes)."""
    catalog_repo, _ = seeded_repos
    session = _Session(_Resp(404, {"detail": "no data for those dates"}))
    conn = WikipediaDemandConnector(Settings(), session=session)
    svc = _demand_service(catalog_repo, conn)

    ctxs = [RouteContext(origin_iata=f"O{i:02d}", dest_iata=f"D{i:02d}",
                         origin_city=f"City{i}", dest_city=f"Dest{i}") for i in range(20)]
    svc.sync(route_contexts=ctxs)
    # One request total, then paused persistently (surfaced as "Rate limited").
    assert len(session.calls) == 1
    state = SqlAlchemyObservationRepository().coverage_for("wikipedia", "demand_signal")
    assert state is not None and state["sync_status"] == "rate_limited"


def _one_ctx() -> list[RouteContext]:
    return [RouteContext(origin_iata="AAA", dest_iata="BBB", origin_city="X", dest_city="Y")]


def test_demand_wikipedia_not_started_next_sync(seeded_repos):
    """Once paused (persisted), the NEXT sync never starts Wikipedia — no network."""
    catalog_repo, _ = seeded_repos
    SqlAlchemyObservationRepository().upsert_sync_state(
        "wikipedia", "demand_signal", "Global", "rate_limited", 0
    )
    session = _Session(_Resp(429, {"detail": "rate limited"}))
    conn = WikipediaDemandConnector(Settings(), session=session)
    _demand_service(catalog_repo, conn).sync(route_contexts=_one_ctx() * 5)
    assert len(session.calls) == 0


def test_demand_wikipedia_pause_surfaces_amber_in_diagnostics(seeded_repos):
    """A Wikipedia failure surfaces as an amber, provider-limited card — never a
    raw HTTP code / "failed" / "not implemented"."""
    catalog_repo, _ = seeded_repos
    session = _Session(_Resp(429, {"detail": "rate limited"}))
    conn = WikipediaDemandConnector(Settings(), session=session)
    _demand_service(catalog_repo, conn).sync(route_contexts=_one_ctx())

    repo = SqlAlchemyObservationRepository()
    assert "wikipedia" in _svc(repo).status()["paused_sources"]

    snap = {"sync": _svc(repo).status(), "demand": {"source_states": {"wikipedia": "available"}}}
    card = {c["name"]: c for c in dg.source_statuses(snap)}["Wikipedia"]
    assert card["emoji"] == "🟡"
    detail = card["detail"] or ""
    assert "HTTP" not in detail and "404" not in detail and "failed" not in detail.lower()


def test_recent_messages_have_no_raw_http_errors(seeded_repos):
    """Recent System Messages must not contain "HTTP 404" / "Connector wikipedia
    failed" — only a single clean provider-limited message."""
    from shared.logging_config import _ring_buffer, configure_logging

    configure_logging("INFO")
    catalog_repo, _ = seeded_repos
    session = _Session(_Resp(404, {"detail": "no data for those dates"}))
    conn = WikipediaDemandConnector(Settings(), session=session)
    svc = _demand_service(catalog_repo, conn)

    start = len(_ring_buffer)
    svc.sync(route_contexts=_one_ctx() * 5)
    new_warnings = [r.getMessage() for r in list(_ring_buffer)[start:] if r.levelno >= logging.WARNING]

    assert not any("HTTP 404" in m or "Connector wikipedia failed" in m for m in new_warnings)
    assert any("provider rate limit reached" in m.lower() for m in new_warnings)


def test_resume_reactivates_wikipedia(seeded_repos):
    """Resume paused sources clears the persisted pause; the next sync starts
    Wikipedia again (READY state) — the only way back, same as AirLabs."""
    repo = SqlAlchemyObservationRepository()
    repo.upsert_sync_state("wikipedia", "demand_signal", "Global", "rate_limited", 0)
    assert _svc(repo).resume_paused_sources() >= 1
    assert repo.coverage_for("wikipedia", "demand_signal")["sync_status"] != "rate_limited"

    catalog_repo, _ = seeded_repos
    session = _Session(_Resp(404, {"detail": "no data"}))
    conn = WikipediaDemandConnector(Settings(), session=session)
    _demand_service(catalog_repo, conn).sync(route_contexts=_one_ctx())
    # No longer disabled → Wikipedia was started again (then re-pauses on its 404).
    assert len(session.calls) >= 1
