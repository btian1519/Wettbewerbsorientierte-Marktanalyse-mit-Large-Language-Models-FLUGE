"""Facade between the Streamlit UI and the FlightScope backend.

Responsibilities (deliberately kept out of the UI):
    * expose dropdown option sources (airlines, continents, tasks);
    * run the backend analysis and adapt its dict payload into typed
      :class:`~services.models.Recommendation` objects;
    * apply the UI-only "Task" as a soft ordering over
      ``market_opportunity_label`` (the backend has no task concept);
    * enrich each recommendation with map coordinates.

Backend import is lazy: option lists come from ``flightscope_backend.core.constants``
(which has no heavy dependencies), while the scoring backend
(``flightscope_backend.services.planning`` → ``src/``) is only imported when an
analysis is actually run. This lets the start page render even if ``src/`` or
its dependencies are not yet installed; the error then surfaces clearly on run.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from flightscope_backend.core.constants import AIRLINES, PLANNING_HORIZON_OPTIONS, REGION_BBOX

from services.geo import build_view_state, coord_for, split_od
from services.models import AnalysisParams, AnalysisResult, Recommendation

# UI Task options → set of backend opportunity labels they emphasise.
# Used as a *soft* filter: matching rows are ordered first, the rest remain
# visible (so the map and result list never silently lose routes).
TASK_OPTIONS: tuple[str, ...] = ("Find new opportunities", "Identify overcapacities")

_TASK_LABEL_MAP: dict[str, frozenset[str]] = {
    "Find new opportunities": frozenset({"white-space", "new-entry", "incumbent-growth"}),
    "Identify overcapacities": frozenset({"defend-or-upgauge"}),
}

DEFAULT_MAX_RECOMMENDATIONS = 25


# --------------------------------------------------------------------------- #
# Option sources for the sidebar / start-page dropdowns
# --------------------------------------------------------------------------- #
def get_airline_options() -> list[tuple[str, str]]:
    """Return ``(code, "CODE — Name")`` pairs for the airline dropdown."""
    return [(code, f"{code} — {meta['name']}") for code, meta in AIRLINES.items()]


def get_continent_options() -> list[str]:
    """Return continent / scope names for the dropdown (``Global`` first)."""
    names = list(REGION_BBOX.keys())
    if "Global" in names:
        names.remove("Global")
        names.insert(0, "Global")
    return names


def get_task_options() -> list[str]:
    """Return the available analysis-task labels."""
    return list(TASK_OPTIONS)


def get_planning_horizon_options() -> dict[str, int]:
    """Return the label → months mapping for the (optional) horizon control."""
    return dict(PLANNING_HORIZON_OPTIONS)


def default_effective_month(today: date | None = None) -> date:
    """Return the first day of the current month (backend seasonality anchor)."""
    today = today or date.today()
    return date(today.year, today.month, 1)


# --------------------------------------------------------------------------- #
# Analysis orchestration
# --------------------------------------------------------------------------- #
def run_analysis(params: AnalysisParams) -> AnalysisResult:
    """Run the backend analysis for *params* and adapt it for the UI.

    Args:
        params: Fully-specified user inputs.

    Returns:
        An :class:`AnalysisResult` with all recommendations (up to the cap),
        the map camera for the selected region, and light backend metadata.

    Raises:
        RuntimeError: If the backend package cannot be imported (missing
            ``src/`` or dependencies), with a clear, actionable message.
    """
    build_analysis = _load_backend()

    raw = build_analysis(
        region=params.region,
        airline_code=params.airline_code,
        effective_month=params.effective_month,
        planning_horizon_months=params.planning_horizon_months,
        num_recommendations=params.num_recommendations,
    )

    report = raw.get("report") or {}
    items = report.get("recommendations") or []
    recommendations = _adapt_recommendations(items, params.task)

    warnings: list[str] = []
    if not recommendations:
        warnings.append(
            "No observed-supported routes were returned. Collect market data "
            "(data/raw) for this region before analysing, or widen the scope."
        )

    return AnalysisResult(
        params=params,
        recommendations=recommendations,
        view_state=build_view_state(params.region),
        generated_at=datetime.now(timezone.utc),
        backend_meta={
            "runtime_context": raw.get("runtime_context", ""),
            "observed_window": raw.get("observed_window", ""),
            "candidate_pool_size": len(raw.get("candidate_routes") or []),
            "total_live_records": (raw.get("collected_data") or {}).get("total_live_records", 0),
        },
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _load_backend():
    """Import and return ``build_analysis`` lazily, with a friendly error."""
    try:
        from flightscope_backend.services.planning import build_analysis
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "FlightScope backend is not importable. Ensure the repo 'src/' "
            "package and 'data/' folder sit at the project root and that "
            f"dependencies (pandas, ...) are installed. Original error: {exc}"
        ) from exc
    return build_analysis


def _adapt_recommendations(items: list[dict], task: str) -> list[Recommendation]:
    """Convert backend recommendation dicts into ordered, enriched models."""
    target_labels = _TASK_LABEL_MAP.get(task, frozenset())
    adapted = [_adapt_one(item, target_labels) for item in items]

    # Soft task ordering: matches first, backend score order preserved within
    # each group. Nothing is dropped, so map/list stay complete and in sync.
    adapted.sort(key=lambda rec: (not rec.task_match, rec.backend_rank))
    for display_rank, rec in enumerate(adapted, start=1):
        rec.display_rank = display_rank
    return adapted


def _adapt_one(item: dict, target_labels: frozenset[str]) -> Recommendation:
    """Adapt a single backend recommendation dict into a :class:`Recommendation`."""
    od = str(item.get("od") or "")
    origin_iata, dest_iata = split_od(od)
    origin_name, dest_name = _split_route_names(str(item.get("route") or ""))
    label = str(item.get("market_opportunity_label") or "")
    rationale = str(item.get("rationale") or "")

    return Recommendation(
        backend_rank=int(item.get("rank") or 0),
        display_rank=int(item.get("rank") or 0),
        od=od,
        route=str(item.get("route") or od),
        origin_name=origin_name or origin_iata,
        dest_name=dest_name or dest_iata,
        origin_iata=origin_iata,
        dest_iata=dest_iata,
        score=float(item.get("score") or 0.0),
        estimated_pax=int(item.get("estimated_pax") or 0),
        aircraft=str(item.get("aircraft") or "n/a"),
        observed_airlines_total=int(item.get("observed_airlines_total") or 0),
        observed_airlines=list(item.get("observed_airlines") or []),
        competitor_count=int(item.get("competitor_count") or 0),
        target_airline_present=bool(item.get("target_airline_present")),
        target_airline_observed_flights=int(item.get("target_airline_observed_flights") or 0),
        market_opportunity_score=float(item.get("market_opportunity_score") or 0.0),
        market_opportunity_label=label,
        rationale_lines=[line.strip() for line in rationale.split("|") if line.strip()],
        origin_coord=coord_for(origin_iata),
        dest_coord=coord_for(dest_iata),
        task_match=label in target_labels,
    )


def _split_route_names(route: str) -> tuple[str, str]:
    """Split a ``"Origin (XXX) → Dest (YYY)"`` route string into its two names."""
    for separator in ("→", "->", " to "):
        if separator in route:
            left, _, right = route.partition(separator)
            return left.strip(), right.strip()
    return route.strip(), ""
