"""Analysis orchestration: query → filter → price → score → rank → present.

This is the single entry point the frontend calls. It composes the pure analysis
components (engine, pricing, ranking, filters) and maps the winning routes to
presentation DTOs enriched with airport master data.
"""

from __future__ import annotations

from time import perf_counter

from backend.analysis.engine import BenefitEngine, ScoredRoute
from backend.analysis.market import validate_scope
from backend.dto import AnalysisRequest, AnalysisResponse, RouteResult
from backend.filters import apply_filters
from backend.pricing import PriceResolver
from backend.ranking import rank_scored
from backend.services.catalog_service import CatalogService
from database.repository.interfaces import RouteRepository
from shared.constants import Task
from shared.logging_config import get_logger

log = get_logger("backend.analysis_service")

_GAP_LABEL = {Task.OPPORTUNITIES: "Market Gap", Task.OVERCAPACITIES: "Overcapacities"}


class AnalysisService:
    def __init__(
        self,
        route_repo: RouteRepository,
        catalog_service: CatalogService,
        engine: BenefitEngine | None = None,
    ) -> None:
        self._routes = route_repo
        self._catalog = catalog_service
        self._engine = engine or BenefitEngine()

    def latest_week(self) -> str:
        weeks = self._routes.distinct_weeks()
        return weeks[-1] if weeks else ""

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        validate_scope(request.scope)
        week = request.week or self.latest_week()
        t0 = perf_counter()

        if request.task == Task.OVERCAPACITIES:
            routes = self._routes.routes_for_airline(request.airline_iata, request.scope, week)
        else:
            routes = self._routes.routes_by_scope(request.scope, week)

        considered = len(routes)
        resolver = PriceResolver(routes, request.airline_iata)  # built over full in-scope set
        filtered = apply_filters(routes, request.filters)

        scored: list[ScoredRoute] = []
        for r in filtered:
            price = resolver.resolve(r)
            scored.append(
                self._engine.score(
                    r, price.price_eur, price.source,
                    request.filters, request.task, request.airline_iata,
                )
            )

        top = rank_scored(scored, request.task)
        results = [self._to_result(i + 1, sr, request.task) for i, sr in enumerate(top)]

        compute_ms = round((perf_counter() - t0) * 1000, 1)
        stats = {
            "task": request.task.value,
            "scope": request.scope,
            "week": week,
            "routes_considered": considered,
            "routes_after_filters": len(filtered),
            "results_returned": len(results),
            "compute_ms": compute_ms,
        }
        log.info(
            "Analysis %s / %s: %d considered -> %d results in %.1f ms",
            request.task.value, request.scope, considered, len(results), compute_ms,
        )
        return AnalysisResponse(
            task=request.task,
            scope=request.scope,
            airline_iata=request.airline_iata,
            week=week,
            results=results,
            stats=stats,
        )

    # ------------------------------------------------------------------ #
    def _to_result(self, rank: int, sr: ScoredRoute, task: Task) -> RouteResult:
        r = sr.route
        origin = self._catalog.airport(r.origin_iata)
        dest = self._catalog.airport(r.dest_iata)
        return RouteResult(
            rank=rank,
            origin_iata=r.origin_iata,
            dest_iata=r.dest_iata,
            origin_name=origin.name if origin else None,
            dest_name=dest.name if dest else None,
            origin_country=origin.country if origin else None,
            dest_country=dest.country if dest else None,
            origin_continent=r.origin_continent,
            dest_continent=r.dest_continent,
            origin_lat=origin.lat if origin else 0.0,
            origin_lon=origin.lon if origin else 0.0,
            dest_lat=dest.lat if dest else 0.0,
            dest_lon=dest.lon if dest else 0.0,
            distance_km=r.distance_km,
            demand=r.total_demand,
            total_supply=float(r.total_supply),
            delta_pax=sr.delta_pax,
            benefit_eur=sr.benefit_eur,
            avg_price_eur=sr.price_eur,
            price_source=sr.price_source,
            num_airlines=r.num_airlines,
            selected_airline_share=sr.airline_share,
            gap_label=_GAP_LABEL[task],
        )
