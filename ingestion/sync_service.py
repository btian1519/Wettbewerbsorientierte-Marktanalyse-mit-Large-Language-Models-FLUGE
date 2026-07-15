"""Data Synchronization Layer — updates the global market database.

This layer has **no knowledge of UI filters**. A sync always targets the whole
available market (all airports → all routes → all airlines per route), never the
airline/continent/task the user happens to have selected. It is driven by the
scheduler or the manual "Sync Now" button; the analysis layer only ever *reads*
what this layer has written.

Each run records both an append-only :class:`SyncRun` (history) and an upserted
:class:`SyncState` (latest coverage per source/category): data_source,
coverage_scope, sync_status, sync_timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from backend.services.catalog_service import CatalogService
from database.repository.observation_repo import SqlAlchemyObservationRepository
from ingestion.connectors import (
    AircraftDbConnector,
    AirLabsConnector,
    ConnectorError,
    OpenFlightsConnector,
)
from ingestion.connectors.base import BaseConnector, ConnectorStatus, QuotaExceededError
from ingestion.normalization import normalize_schedules
from shared.config import Settings, get_settings
from shared.logging_config import get_logger
from shared.rate_limit import RATE_LIMIT_STATUS, looks_rate_limited as _looks_rate_limited
from shared.sources import DataSource, SyncCategory

log = get_logger("ingestion.sync_service")

# Abort a market crawl after this many consecutive connector failures (outage).
_CIRCUIT_BREAKER_FAILURES = 5


def current_iso_week() -> str:
    iso = datetime.now(timezone.utc).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


@dataclass
class SyncResult:
    source: str
    category: str
    status: str
    coverage_scope: str | None = None
    records: int = 0
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class SyncService:
    """Coordinates connectors, normalizers and the observation repository."""

    def __init__(
        self,
        obs_repo: SqlAlchemyObservationRepository,
        catalog_service: CatalogService,
        connectors: dict[DataSource, BaseConnector],
        aircraft_db: AircraftDbConnector,
        settings: Settings | None = None,
        demand_service=None,
    ) -> None:
        self._repo = obs_repo
        self._catalog = catalog_service
        self._connectors = connectors
        self._aircraft = aircraft_db
        self._settings = settings or get_settings()
        self._demand_service = demand_service  # Demand Data Platform (optional)

    # ================================================================== #
    # Public entry points (UI-independent)
    # ================================================================== #
    def sync_market(self) -> list[SyncResult]:
        """Full market update — what "Sync Now" and a full scheduler pass run.

        Independent of any UI selection: refreshes global supply and demand.
        """
        log.info("Market sync started (global; independent of UI state)")
        return [self.sync_supply(), self.sync_demand()]

    # ------------------------------------------------------------------ #
    # Supply (AirLabs) — the whole market
    # ------------------------------------------------------------------ #
    def sync_supply(self, week: str | None = None) -> SyncResult:
        result = SyncResult(DataSource.AIRLABS.value, SyncCategory.SCHEDULES.value, "running")
        if self._is_paused(result.source, result.category):
            return self._skip_paused(result)
        connector = self._connectors.get(DataSource.AIRLABS)
        week = week or current_iso_week()
        snapshot = date.today()
        try:
            if not isinstance(connector, AirLabsConnector) or not connector.is_configured():
                raise ConnectorError("AirLabs connector not configured (set AIRLABS_API_KEY)")

            # Fail fast on an outage: one cheap probe before crawling the market.
            if connector.probe().reachable is False:
                raise ConnectorError("AirLabs unreachable (probe failed) — skipping market crawl")

            deps, result.coverage_scope = self._market_departure_airports()
            schedules = []
            # Circuit breaker: if the source is unreachable, abort the whole crawl
            # fast instead of hammering hundreds of airports (protects the button
            # and the scheduler from long hangs on an outage).
            consecutive_failures = 0
            for dep in deps:
                try:
                    schedules.extend(connector.fetch_routes(dep))
                    consecutive_failures = 0
                except QuotaExceededError as exc:
                    # Quota is gone — every further request returns the same error.
                    # Stop immediately with a clear, actionable message.
                    raise ConnectorError(f"{exc}. Bound the crawl with SYNC_MAX_AIRPORTS, "
                                         "use another API key, or wait for the quota to reset.") from exc
                except ConnectorError as exc:
                    consecutive_failures += 1
                    log.warning("AirLabs fetch failed for %s: %s", dep, exc)
                    if consecutive_failures >= _CIRCUIT_BREAKER_FAILURES:
                        # Reachable but failing on every request — carry the real
                        # underlying reason instead of a generic "unreachable".
                        raise ConnectorError(
                            f"AirLabs failed on {consecutive_failures} consecutive requests: {exc}"
                        ) from exc

            rows = normalize_schedules(
                schedules,
                week=week,
                snapshot_date=snapshot,
                resolve_route_id=self._repo.resolve_route_id,
                seats_for=self._aircraft.seats_for,
                source=DataSource.AIRLABS.value,
            )
            result.records = self._repo.save_supply_snapshot(rows)
            result.status = "success"
        except Exception as exc:  # noqa: BLE001 - audit every failure
            result.status = "error"
            result.error = str(exc)[:500]
            log.error("Supply sync failed: %s", exc)
        finally:
            self._finalize(result)
        return result

    def _market_departure_airports(self) -> tuple[list[str], str]:
        """ALL catalogued airports (full market), optionally capped for rate limits.

        When capped (e.g. AirLabs free tier), airline hub airports are crawled
        first so the limited request budget captures the busiest routes.
        """
        all_iatas = [a.iata for a in self._catalog.airports]
        cap = self._settings.sync_max_airports
        if cap and cap > 0:
            bases = {a.base_iata for a in self._catalog.airlines if a.base_iata}
            ordered = [i for i in all_iatas if i in bases] + [i for i in all_iatas if i not in bases]
            deps = ordered[:cap]
        else:
            deps = all_iatas
        scope = "Global" if len(deps) >= len(all_iatas) else f"Partial ({len(deps)} airports)"
        return deps, scope

    # ------------------------------------------------------------------ #
    # Demand (prepared) — the whole market
    # ------------------------------------------------------------------ #
    def sync_demand(self, week: str | None = None) -> SyncResult:
        """Delegate to the Demand Data Platform (global; UI-independent)."""
        result = SyncResult(
            DataSource.GOOGLE_TRENDS.value, SyncCategory.DEMAND.value, "skipped", coverage_scope="Global"
        )
        if self._is_paused(result.source, result.category):
            return self._skip_paused(result)
        try:
            if self._demand_service is None:
                result.error = "demand service not wired"
            else:
                dr = self._demand_service.sync(week=week)
                result.status = dr.status
                result.records = dr.normalized
                result.error = dr.error
        except Exception as exc:  # noqa: BLE001
            result.status = "error"
            result.error = str(exc)[:500]
        finally:
            self._finalize(result)
        return result

    # ------------------------------------------------------------------ #
    # Airport metadata (OpenFlights) — monthly; enriches gaps, never overwrites
    # ------------------------------------------------------------------ #
    def sync_airport_metadata(self) -> SyncResult:
        result = SyncResult(
            DataSource.OPENFLIGHTS.value, SyncCategory.AIRPORT_METADATA.value, "running", coverage_scope="Global"
        )
        if self._is_paused(result.source, result.category):
            return self._skip_paused(result)
        connector = self._connectors.get(DataSource.OPENFLIGHTS)
        try:
            if not isinstance(connector, OpenFlightsConnector):
                raise ConnectorError("OpenFlights connector unavailable")
            records = connector.fetch_airports()
            # Only fills NULL fields of existing airports; never adds airports or
            # overwrites AIRPORTS-file data.
            result.records = self._repo.enrich_airports([r.model_dump() for r in records])
            result.status = "success"
        except Exception as exc:  # noqa: BLE001
            result.status = "error"
            result.error = str(exc)[:500]
            log.error("Airport metadata sync failed: %s", exc)
        finally:
            self._finalize(result)
        return result

    # ================================================================== #
    # Scheduler dispatch (same behaviour as "Sync Now" per category)
    # ================================================================== #
    def run_category(self, category: SyncCategory) -> SyncResult | None:
        if category in (SyncCategory.SCHEDULES, SyncCategory.PRICES):
            return self.sync_supply()
        if category == SyncCategory.DEMAND:
            return self.sync_demand()
        if category == SyncCategory.AIRPORT_METADATA:
            return self.sync_airport_metadata()
        return None

    # ------------------------------------------------------------------ #
    # Rate-limit circuit breaker (persisted, per source/category)
    # ------------------------------------------------------------------ #
    def _is_paused(self, source: str, category: str) -> bool:
        """Whether this source/category was paused by an earlier provider limit."""
        state = self._repo.coverage_for(source, category)
        return bool(state and state["sync_status"] == RATE_LIMIT_STATUS)

    def _skip_paused(self, result: SyncResult) -> SyncResult:
        """Record a skipped run for a paused source WITHOUT clearing its paused state."""
        result.status = "skipped"
        result.error = "Paused — provider rate/quota limit reached; sync stopped for this source."
        result.finished_at = datetime.now(timezone.utc)
        self._record_run(result)  # history only; the persisted pause stays in place
        log.info("Skipping %s/%s — paused after an earlier provider limit.",
                 result.source, result.category)
        return result

    def resume_paused_sources(self) -> int:
        """Clear all persisted rate-limit pauses so those sources sync again."""
        resumed = self._repo.clear_sync_status(RATE_LIMIT_STATUS)
        if resumed:
            log.info("Resumed %d rate-limited source(s).", resumed)
        return resumed

    def _record_run(self, result: SyncResult) -> None:
        self._repo.record_sync_run(
            {
                "source": result.source,
                "category": result.category,
                "coverage_scope": result.coverage_scope,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "status": result.status,
                "records_written": result.records,
                "error": result.error,
            }
        )

    def _finalize(self, result: SyncResult) -> None:
        result.finished_at = result.finished_at or datetime.now(timezone.utc)
        # A provider usage limit (429 / quota) pauses this source: persist a distinct
        # status so future syncs skip it, and it stays paused across restarts.
        if result.status == "error" and _looks_rate_limited(result.error):
            result.status = RATE_LIMIT_STATUS
            log.warning("Source %s/%s hit a provider limit — pausing future syncs (persisted).",
                        result.source, result.category)
        self._record_run(result)
        self._repo.upsert_sync_state(
            data_source=result.source,
            category=result.category,
            coverage_scope=result.coverage_scope,
            sync_status=result.status,
            records=result.records,
        )

    # ================================================================== #
    # Status (dev footer — Data Status)
    # ================================================================== #
    def connector_statuses(self) -> list[ConnectorStatus]:
        return [c.status() for c in self._connectors.values()]

    def status(self) -> dict:
        states = self._repo.sync_states()
        return {
            "connectors": {c.source.value: c.status().label for c in self._connectors.values()},
            "counts": self._repo.counts(),
            "last_supply_refresh": self._repo.last_supply_refresh(),
            "last_demand_refresh": self._repo.last_demand_refresh(),
            "coverage": states,
            # Sources paused after a provider rate/quota limit (persisted).
            "paused_sources": sorted(
                {s["data_source"] for s in states if s["sync_status"] == RATE_LIMIT_STATUS}
            ),
            "recent_runs": self._repo.last_sync_runs(limit=5),
        }
