"""Repositories for the live-data (historical) tables.

* :class:`SqlAlchemyObservationRepository` — writes supply/demand snapshots,
  resolves/creates canonical routes, records sync runs, and reports counts &
  last-refresh times for the dev footer.
* :class:`SqlAlchemyLiveRouteRepository` — reads the latest snapshot back as the
  neutral :class:`~database.repository.interfaces.RouteRead` model, so the
  unchanged analysis engine can run on live data exactly like on demo data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Protocol, Sequence

from sqlalchemy import func, insert, select

from database.base import session_scope
from database.models import (
    Airport,
    DemandObservation,
    Route,
    SupplyObservation,
    SyncRun,
    SyncState,
    TrendObservation,
)
from database.repository.interfaces import OfferRead, RouteRead
from shared.constants import INTERCONTINENTAL
from shared.logging_config import get_logger
from shared.utils import haversine_km

log = get_logger("database.observation_repo")


class SqlAlchemyObservationRepository:
    """Writes + bookkeeping for the live-data tables."""

    def __init__(self) -> None:
        self._route_cache: dict[tuple[str, str], int] = {}
        self._airports: dict[str, tuple[float, float, str]] | None = None

    # -- airports (for route enrichment) ------------------------------- #
    def _airport_index(self) -> dict[str, tuple[float, float, str]]:
        if self._airports is None:
            with session_scope() as s:
                self._airports = {
                    a.iata: (a.lat, a.lon, a.continent) for a in s.execute(select(Airport)).scalars()
                }
        return self._airports

    def _route_meta(self, origin: str, dest: str) -> tuple[float | None, str | None]:
        idx = self._airport_index()
        o, d = idx.get(origin), idx.get(dest)
        if not (o and d):
            return None, None
        distance = round(haversine_km(o[0], o[1], d[0], d[1]), 1)
        category = o[2] if o[2] == d[2] else INTERCONTINENTAL
        return distance, category

    def resolve_route_id(self, origin: str, dest: str) -> int:
        """Upsert a canonical route and return its id (cached)."""
        key = (origin, dest)
        if key in self._route_cache:
            return self._route_cache[key]
        with session_scope() as s:
            existing = s.execute(
                select(Route.id).where(Route.origin_iata == origin, Route.dest_iata == dest)
            ).scalar_one_or_none()
            if existing is None:
                distance, category = self._route_meta(origin, dest)
                route = Route(origin_iata=origin, dest_iata=dest, distance_km=distance, continent_category=category)
                s.add(route)
                s.flush()
                existing = route.id
        self._route_cache[key] = int(existing)
        return int(existing)

    # -- metadata enrichment (never overwrites, never adds airports) --- #
    def enrich_airports(self, records: Sequence[dict]) -> int:
        """Fill NULL name/country of existing airports from external metadata.

        Only touches rows that already exist (airports come solely from
        AIRPORTS.xlsx) and only where the current value is NULL — existing data is
        never overwritten. Returns the number of fields filled.
        """
        by_iata = {r["iata"]: r for r in records if r.get("iata")}
        filled = 0
        with session_scope() as s:
            for a in s.execute(select(Airport)).scalars():
                rec = by_iata.get(a.iata)
                if not rec:
                    continue
                if a.name is None and rec.get("name"):
                    a.name = rec["name"]
                    filled += 1
                if a.country is None and rec.get("country"):
                    a.country = rec["country"]
                    filled += 1
        self._airports = None  # invalidate cached index
        log.info("Airport metadata enrichment filled %d fields", filled)
        return filled

    # -- snapshot writes ----------------------------------------------- #
    def save_supply_snapshot(self, rows: Sequence[dict]) -> int:
        if not rows:
            return 0
        with session_scope() as s:
            s.execute(insert(SupplyObservation), list(rows))
        log.info("Saved %d supply observations", len(rows))
        return len(rows)

    def save_demand_snapshot(self, rows: Sequence[dict]) -> int:
        if not rows:
            return 0
        with session_scope() as s:
            s.execute(insert(DemandObservation), list(rows))
        log.info("Saved %d demand observations", len(rows))
        return len(rows)

    def save_trend_points(self, rows: Sequence[dict]) -> int:
        if not rows:
            return 0
        with session_scope() as s:
            s.execute(insert(TrendObservation), list(rows))
        return len(rows)

    # -- sync-run audit ------------------------------------------------ #
    def record_sync_run(self, run: dict) -> None:
        with session_scope() as s:
            s.execute(insert(SyncRun), [run])

    def last_sync_runs(self, limit: int = 20) -> list[dict]:
        with session_scope() as s:
            rows = s.execute(select(SyncRun).order_by(SyncRun.started_at.desc()).limit(limit)).scalars().all()
            return [
                {
                    "source": r.source, "category": r.category, "status": r.status,
                    "coverage_scope": r.coverage_scope,
                    "started_at": r.started_at, "finished_at": r.finished_at,
                    "records": r.records_written, "error": r.error,
                }
                for r in rows
            ]

    # -- coverage state (latest per source/category) ------------------- #
    def upsert_sync_state(
        self, data_source: str, category: str, coverage_scope: str | None, sync_status: str, records: int
    ) -> None:
        with session_scope() as s:
            existing = s.execute(
                select(SyncState).where(SyncState.data_source == data_source, SyncState.category == category)
            ).scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if existing is not None:
                existing.coverage_scope = coverage_scope
                existing.sync_status = sync_status
                existing.records = records
                existing.sync_timestamp = now
            else:
                s.add(SyncState(
                    data_source=data_source, category=category, coverage_scope=coverage_scope,
                    sync_status=sync_status, records=records, sync_timestamp=now,
                ))

    def known_routes(self) -> list[tuple[str, str]]:
        """All canonical (origin, destination) routes discovered so far."""
        with session_scope() as s:
            return [(o, d) for o, d in s.execute(select(Route.origin_iata, Route.dest_iata)).all()]

    def sync_states(self) -> list[dict]:
        with session_scope() as s:
            rows = s.execute(select(SyncState).order_by(SyncState.data_source)).scalars().all()
            return [
                {
                    "data_source": r.data_source, "category": r.category,
                    "coverage_scope": r.coverage_scope, "sync_status": r.sync_status,
                    "records": r.records, "sync_timestamp": r.sync_timestamp,
                }
                for r in rows
            ]

    def coverage_for(self, data_source: str, category: str) -> dict | None:
        for state in self.sync_states():
            if state["data_source"] == data_source and state["category"] == category:
                return state
        return None

    # -- status / counts ----------------------------------------------- #
    def counts(self) -> dict:
        with session_scope() as s:
            def n(model) -> int:
                return int(s.scalar(select(func.count()).select_from(model)) or 0)

            supply_snaps = s.scalar(select(func.count(func.distinct(SupplyObservation.snapshot_date)))) or 0
            demand_snaps = s.scalar(select(func.count(func.distinct(DemandObservation.snapshot_date)))) or 0
            return {
                "routes": n(Route),
                "supply_observations": n(SupplyObservation),
                "demand_observations": n(DemandObservation),
                "trend_observations": n(TrendObservation),
                "supply_snapshots": int(supply_snaps),
                "demand_snapshots": int(demand_snaps),
                "sync_runs": n(SyncRun),
            }

    def last_supply_refresh(self) -> datetime | None:
        with session_scope() as s:
            return s.scalar(select(func.max(SupplyObservation.created_at)))

    def last_demand_refresh(self) -> datetime | None:
        with session_scope() as s:
            return s.scalar(select(func.max(DemandObservation.created_at)))


class DemandProvider(Protocol):
    """Minimal demand contract the live repo depends on (structural typing)."""

    def get_weekly_demand(self, origin: str, destination: str, week: str): ...


class SqlAlchemyLiveRouteRepository:
    """Reads the latest live snapshot as neutral RouteRead objects.

    Implements the read side of the ``RouteRepository`` contract used by the
    analysis service (``distinct_weeks`` / ``routes_by_scope`` /
    ``routes_for_airline``); write methods are intentionally unsupported here.

    Demand is obtained *only* through the injected demand provider's
    ``get_weekly_demand`` — the repo has no knowledge of how demand is computed.
    """

    def __init__(self, demand_provider: "DemandProvider | None" = None) -> None:
        self._demand = demand_provider

    def distinct_weeks(self) -> list[str]:
        with session_scope() as s:
            return list(s.scalars(select(SupplyObservation.week).distinct().order_by(SupplyObservation.week)).all())

    def routes_by_scope(self, scope: str, week: str) -> list[RouteRead]:
        with session_scope() as s:
            route_rows = s.execute(
                select(Route).where(Route.continent_category == scope)
            ).scalars().all()
            return self._assemble(s, route_rows, week)

    def routes_for_airline(self, airline_iata: str, scope: str, week: str) -> list[RouteRead]:
        with session_scope() as s:
            route_ids = s.scalars(
                select(SupplyObservation.route_id)
                .where(SupplyObservation.airline_iata == airline_iata, SupplyObservation.week == week)
                .distinct()
            ).all()
            if not route_ids:
                return []
            route_rows = s.execute(
                select(Route).where(Route.id.in_(route_ids), Route.continent_category == scope)
            ).scalars().all()
            return self._assemble(s, route_rows, week)

    # ------------------------------------------------------------------ #
    def _assemble(self, session, route_rows: Sequence[Route], week: str) -> list[RouteRead]:
        ids = [r.id for r in route_rows]
        if not ids:
            return []
        supply_by_route: dict[int, list[OfferRead]] = defaultdict(list)

        for i in range(0, len(ids), 900):
            batch = ids[i : i + 900]
            for o in session.execute(
                select(SupplyObservation).where(
                    SupplyObservation.route_id.in_(batch), SupplyObservation.week == week
                )
            ).scalars():
                seats_per_flight = int(o.available_seats / o.frequency) if o.frequency else o.available_seats
                supply_by_route[o.route_id].append(
                    OfferRead(o.airline_iata, seats_per_flight, o.frequency, o.available_seats, o.average_price or 0.0)
                )

        # Demand comes solely from the demand provider's get_weekly_demand.
        def _demand_for(origin: str, dest: str) -> float:
            if self._demand is None:
                return 0.0
            wd = self._demand.get_weekly_demand(origin, dest, week)
            return float(wd.estimated_weekly_passengers) if wd else 0.0

        # Batch-load endpoint continents in one query.
        iatas = {r.origin_iata for r in route_rows} | {r.dest_iata for r in route_rows}
        cont = {
            iata: c
            for iata, c in session.execute(
                select(Airport.iata, Airport.continent).where(Airport.iata.in_(iatas))
            ).all()
        }

        out: list[RouteRead] = []
        for route in route_rows:
            scope = route.continent_category or ""
            out.append(
                RouteRead(
                    id=route.id,
                    week=week,
                    origin_iata=route.origin_iata,
                    dest_iata=route.dest_iata,
                    origin_continent=cont.get(route.origin_iata, scope),
                    dest_continent=cont.get(route.dest_iata, scope),
                    scope=scope,
                    distance_km=route.distance_km or 0.0,
                    total_demand=_demand_for(route.origin_iata, route.dest_iata),
                    offers=tuple(supply_by_route.get(route.id, ())),
                )
            )
        return out
