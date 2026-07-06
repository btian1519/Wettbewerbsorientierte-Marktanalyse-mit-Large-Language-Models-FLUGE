"""Concrete SQLAlchemy implementation of the repository contracts.

Bulk writes use Core ``insert`` with executemany for speed (the demo generator
loads ~35k routes and ~100k offers). Reads return neutral read-models assembled
in Python with a bounded number of queries (no per-row lazy loading).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from database.base import session_scope
from database.models import Airline, AirlineOffer, Airport, RouteWeek
from database.repository.interfaces import (
    AirlineRead,
    AirportRead,
    OfferRead,
    RouteRead,
)
from shared.logging_config import get_logger

log = get_logger("database.repository")

_INSERT_CHUNK = 5000


def _chunked(rows: Sequence[dict], size: int = _INSERT_CHUNK):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


class SqlAlchemyCatalogRepository:
    """Airports & airlines master data access."""

    def replace_airports(self, rows: Sequence[dict]) -> None:
        with session_scope() as s:
            s.execute(delete(Airport))
            for chunk in _chunked(list(rows)):
                s.execute(insert(Airport), list(chunk))
        log.info("Loaded %d airports", len(rows))

    def replace_airlines(self, rows: Sequence[dict]) -> None:
        with session_scope() as s:
            s.execute(delete(Airline))
            for chunk in _chunked(list(rows)):
                s.execute(insert(Airline), list(chunk))
        log.info("Loaded %d airlines", len(rows))

    def list_airports(self) -> list[AirportRead]:
        with session_scope() as s:
            rows = s.execute(select(Airport)).scalars().all()
            return [
                AirportRead(a.iata, a.name, a.country, a.lon, a.lat, a.continent)
                for a in rows
            ]

    def list_airlines(self) -> list[AirlineRead]:
        with session_scope() as s:
            rows = s.execute(select(Airline)).scalars().all()
            return [
                AirlineRead(a.iata, a.name, a.base, a.region, a.base_iata)
                for a in rows
            ]

    def airport_count(self) -> int:
        with session_scope() as s:
            return int(s.scalar(select(func.count()).select_from(Airport)) or 0)

    def airline_count(self) -> int:
        with session_scope() as s:
            return int(s.scalar(select(func.count()).select_from(Airline)) or 0)


class SqlAlchemyRouteRepository:
    """Weekly route supply/demand access."""

    def bulk_load(self, route_rows: Sequence[dict], offer_rows: Sequence[dict]) -> None:
        with session_scope() as s:
            for chunk in _chunked(list(route_rows)):
                s.execute(insert(RouteWeek), list(chunk))
            for chunk in _chunked(list(offer_rows)):
                s.execute(insert(AirlineOffer), list(chunk))
        log.info("Loaded %d routes and %d offers", len(route_rows), len(offer_rows))

    def clear_routes(self) -> None:
        with session_scope() as s:
            s.execute(delete(AirlineOffer))
            s.execute(delete(RouteWeek))
        log.info("Cleared route/offer tables")

    def route_count(self, week: str | None = None) -> int:
        with session_scope() as s:
            stmt = select(func.count()).select_from(RouteWeek)
            if week:
                stmt = stmt.where(RouteWeek.week == week)
            return int(s.scalar(stmt) or 0)

    def offer_count(self) -> int:
        with session_scope() as s:
            return int(s.scalar(select(func.count()).select_from(AirlineOffer)) or 0)

    def distinct_weeks(self) -> list[str]:
        with session_scope() as s:
            return list(s.scalars(select(RouteWeek.week).distinct().order_by(RouteWeek.week)).all())

    def route_count_by_scope(self, week: str) -> dict[str, int]:
        with session_scope() as s:
            rows = s.execute(
                select(RouteWeek.scope, func.count())
                .where(RouteWeek.week == week)
                .group_by(RouteWeek.scope)
            ).all()
            return {scope: int(n) for scope, n in rows}

    # -- assembly of read-models -------------------------------------------- #
    def routes_by_scope(self, scope: str, week: str) -> list[RouteRead]:
        with session_scope() as s:
            routes = s.execute(
                select(RouteWeek).where(RouteWeek.week == week, RouteWeek.scope == scope)
            ).scalars().all()
            return self._attach_offers(s, routes)

    def routes_for_airline(self, airline_iata: str, scope: str, week: str) -> list[RouteRead]:
        with session_scope() as s:
            route_ids = s.scalars(
                select(AirlineOffer.route_week_id)
                .join(RouteWeek, RouteWeek.id == AirlineOffer.route_week_id)
                .where(
                    AirlineOffer.airline_iata == airline_iata,
                    RouteWeek.week == week,
                    RouteWeek.scope == scope,
                )
                .distinct()
            ).all()
            if not route_ids:
                return []
            routes = s.execute(
                select(RouteWeek).where(RouteWeek.id.in_(route_ids))
            ).scalars().all()
            return self._attach_offers(s, routes)

    @staticmethod
    def _attach_offers(session: Session, routes: Sequence[RouteWeek]) -> list[RouteRead]:
        ids = [r.id for r in routes]
        offers_by_route: dict[int, list[OfferRead]] = defaultdict(list)
        if ids:
            # Query offers in bounded batches to avoid oversized IN clauses.
            for i in range(0, len(ids), 900):
                batch = ids[i : i + 900]
                for o in session.execute(
                    select(AirlineOffer).where(AirlineOffer.route_week_id.in_(batch))
                ).scalars():
                    offers_by_route[o.route_week_id].append(
                        OfferRead(o.airline_iata, o.seats_per_flight, o.frequency, o.capacity, o.avg_price_eur)
                    )
        return [
            RouteRead(
                id=r.id,
                week=r.week,
                origin_iata=r.origin_iata,
                dest_iata=r.dest_iata,
                origin_continent=r.origin_continent,
                dest_continent=r.dest_continent,
                scope=r.scope,
                distance_km=r.distance_km,
                total_demand=r.total_demand,
                offers=tuple(offers_by_route.get(r.id, ())),
            )
            for r in routes
        ]
