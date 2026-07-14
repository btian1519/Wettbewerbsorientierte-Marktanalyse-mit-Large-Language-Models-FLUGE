"""Demand service — orchestrates the pipeline and owns the analysis contract.

Pipeline (all local, no UI involvement):

    connectors → raw signals (stored) → normalization → model → calibration →
    demand_normalized (stored)

The analysis engine may use **only** :meth:`get_weekly_demand`; it has no
knowledge of Google Trends, Wikipedia, Eurostat, normalization or calibration.
The rule-based model is injected (:class:`DemandModel`), so an ML forecaster can
replace it later without changing this service or the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from backend.services.catalog_service import CatalogService
from database.repository.demand_repo import SqlAlchemyDemandRepository
from database.repository.observation_repo import SqlAlchemyObservationRepository
from ingestion.calibration import CalibrationContext, CalibrationLayer
from ingestion.connectors.base import ConnectorError
from ingestion.demand.base import DemandConnector
from ingestion.demand.model import DemandModel, RuleBasedDemandModelV1
from ingestion.demand.records import RawSignal, RouteContext, WeeklyDemand
from ingestion.normalization.demand_normalizer import build_signal_scores
from shared.config import Settings, get_settings
from shared.logging_config import get_logger
from shared.utils import haversine_km

log = get_logger("backend.demand_service")


def current_iso_week() -> str:
    iso = datetime.now(timezone.utc).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


@dataclass
class DemandSyncResult:
    week: str
    status: str
    coverage_scope: str = "Global"
    signals: int = 0
    normalized: int = 0
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class DemandService:
    def __init__(
        self,
        demand_repo: SqlAlchemyDemandRepository,
        obs_repo: SqlAlchemyObservationRepository,
        catalog_service: CatalogService,
        connectors: list[DemandConnector],
        model: DemandModel | None = None,
        calibration: CalibrationLayer | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._demand = demand_repo
        self._obs = obs_repo
        self._catalog = catalog_service
        self._connectors = connectors
        self._model = model or RuleBasedDemandModelV1()
        self._cal = calibration or CalibrationLayer()
        self._settings = settings or get_settings()

    # ================================================================== #
    # Analysis-engine contract (the ONLY demand entry point)
    # ================================================================== #
    def get_weekly_demand(self, origin: str, destination: str, week: str) -> WeeklyDemand | None:
        nd = self._demand.get_weekly_demand(origin, destination, week)
        if nd is None:
            return None
        return WeeklyDemand(
            origin=origin, destination=destination, week=week,
            estimated_weekly_passengers=nd.estimated_weekly_passengers,
            demand_index=nd.demand_index, confidence_score=nd.confidence_score,
        )

    # ================================================================== #
    # Computation (pure of network — testable with synthetic signals)
    # ================================================================== #
    def compute_from_signals(
        self, raw_signals: list[RawSignal], *, week: str, snapshot_date: date | None = None
    ) -> int:
        snapshot_date = snapshot_date or date.today()

        # 1) persist raw signals
        raw_rows = [
            {
                "route_id": self._obs.resolve_route_id(s.origin_airport, s.destination_airport),
                "origin_airport": s.origin_airport, "destination_airport": s.destination_airport,
                "signal_type": s.signal_type, "signal_value": s.signal_value,
                "search_term": s.search_term, "source": s.source, "week": s.week or week,
                "snapshot_date": snapshot_date, "timestamp": s.timestamp,
            }
            for s in raw_signals
        ]
        self._demand.save_raw_signals(raw_rows)

        # 2) normalize → 3) model → 4) calibrate → confidence
        scores = build_signal_scores(raw_signals)
        norm_rows: list[dict] = []
        for (origin, dest), sig in scores.items():
            comp = self._model.compute(sig)
            route_id = self._obs.resolve_route_id(origin, dest)
            factor = self._demand.calibration_factor(route_id)
            has_history = self._demand.has_history(origin, dest, week)

            if factor is not None:
                estimated = self._cal.estimate_calibrated(comp.demand_index, factor)
                calibrated = True
            else:
                estimated = self._cal.fallback_estimate(comp.demand_index, self._context(origin, dest))
                calibrated = False
            confidence = self._cal.confidence(comp.weight_coverage, calibrated=calibrated, has_history=has_history)

            norm_rows.append({
                "route_id": route_id, "origin_airport": origin, "destination_airport": dest, "week": week,
                "google_score": sig.google, "wikipedia_score": sig.wikipedia, "tourism_score": sig.tourism,
                "population_score": sig.population, "gdp_score": sig.gdp, "event_score": sig.event,
                "demand_index": comp.demand_index, "estimated_weekly_passengers": estimated,
                "confidence_score": confidence, "calculation_version": comp.calculation_version,
                "snapshot_date": snapshot_date,
            })
        return self._demand.save_normalized(norm_rows)

    def _context(self, origin: str, dest: str) -> CalibrationContext:
        o, d = self._catalog.airport(origin), self._catalog.airport(dest)
        distance = haversine_km(o.lat, o.lon, d.lat, d.lon) if (o and d) else None
        return CalibrationContext(distance_km=distance)

    # ================================================================== #
    # Global sync (independent of UI selection)
    # ================================================================== #
    def sync(self, week: str | None = None, route_contexts: list[RouteContext] | None = None) -> DemandSyncResult:
        week = week or current_iso_week()
        result = DemandSyncResult(week=week, status="running")
        try:
            contexts = route_contexts if route_contexts is not None else self._market_route_contexts()
            signals: list[RawSignal] = []
            for ctx in contexts:
                for conn in self._connectors:
                    if not conn.available():
                        continue
                    try:
                        signals.extend(conn.fetch(ctx, week))
                    except ConnectorError as exc:
                        log.warning("Demand connector %s failed for %s-%s: %s",
                                    getattr(conn, "signal_type", "?"), ctx.origin_iata, ctx.dest_iata, exc)
            result.signals = len(signals)
            result.normalized = self.compute_from_signals(signals, week=week)
            result.status = "success" if signals else "skipped"
            if not signals:
                result.error = "no demand signals fetched (connectors unavailable/offline)"
        except Exception as exc:  # noqa: BLE001
            result.status = "error"
            result.error = str(exc)[:500]
            log.error("Demand sync failed: %s", exc)
        finally:
            result.finished_at = datetime.now(timezone.utc)
        return result

    def _market_route_contexts(self) -> list[RouteContext]:
        """O-D pairs generated **independently of supply**, from the AIRPORTS catalog.

        Demand coverage does not depend on which routes AirLabs has discovered — it
        builds its own universe. Airline hubs are prioritised and the set is bounded
        (``DEMAND_MAX_AIRPORTS`` / ``DEMAND_MAX_ROUTES``) because demand proxies are
        rate-limited; raising the caps widens coverage toward all possible O-D pairs.
        """
        airports = list(self._catalog.airports)
        bases = {a.base_iata for a in self._catalog.airlines if a.base_iata}
        pool = [a for a in airports if a.iata in bases] + [a for a in airports if a.iata not in bases]
        if self._settings.demand_max_airports > 0:
            pool = pool[: self._settings.demand_max_airports]

        max_routes = self._settings.demand_max_routes
        contexts: list[RouteContext] = []
        for o in pool:
            for d in pool:
                if o.iata == d.iata:
                    continue
                contexts.append(RouteContext(
                    origin_iata=o.iata, dest_iata=d.iata,
                    origin_city=o.name, dest_city=d.name,
                ))
                if max_routes and len(contexts) >= max_routes:
                    return contexts
        return contexts

    # ================================================================== #
    def status(self) -> dict:
        s = self._demand.status()
        s["sources"] = {getattr(c, "signal_type", "?"): ("available" if c.available() else "unavailable")
                        for c in self._connectors}
        return s
