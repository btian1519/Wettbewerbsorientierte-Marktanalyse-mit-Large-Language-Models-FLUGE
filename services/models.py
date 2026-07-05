"""Typed data models shared between the service layer and the UI.

These dataclasses are the stable contract the Streamlit UI renders against.
They intentionally decouple the UI from the raw backend dictionaries (whose
keys come from ``src/recommendation_engine.generate_recommendation_report``),
so a change in the backend payload only has to be absorbed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

Coordinate = tuple[float, float]  # (latitude, longitude)


@dataclass(frozen=True)
class AnalysisParams:
    """User-selected inputs that fully determine an analysis run.

    Attributes:
        airline_code: Two-letter IATA airline code (key of ``AIRLINES``).
        region: Continent / scope name (key of ``REGION_BBOX``).
        task: High-level analysis intent shown in the UI (see
            ``analysis_service.TASK_OPTIONS``). Applied as a soft filter over
            ``market_opportunity_label`` in the service layer.
        effective_month: First day of the month driving the seasonality
            scenario in the backend.
        planning_horizon_months: Planning window length in months.
        num_recommendations: Upper bound of recommendations to compute. A
            generous cap is requested once so "Show more" reveals cached rows
            instead of recomputing.
    """

    airline_code: str
    region: str
    task: str
    effective_month: date
    planning_horizon_months: int = 3
    num_recommendations: int = 25


@dataclass
class Recommendation:
    """A single route recommendation, enriched with map geometry.

    Mirrors one entry of the backend ``report["recommendations"]`` list, plus
    resolved airport coordinates for the map. ``display_rank`` is the position
    after task ordering; ``backend_rank`` is the backend's score-based rank.
    """

    backend_rank: int
    display_rank: int
    od: str
    route: str
    origin_name: str
    dest_name: str
    origin_iata: str
    dest_iata: str
    score: float
    estimated_pax: int
    aircraft: str
    observed_airlines_total: int
    observed_airlines: list[str]
    competitor_count: int
    target_airline_present: bool
    target_airline_observed_flights: int
    market_opportunity_score: float
    market_opportunity_label: str
    rationale_lines: list[str]
    origin_coord: Coordinate | None
    dest_coord: Coordinate | None
    task_match: bool

    @property
    def has_geometry(self) -> bool:
        """True when both endpoints resolved to coordinates (map-drawable)."""
        return self.origin_coord is not None and self.dest_coord is not None

    @property
    def benefit_label(self) -> str:
        """Human-readable benefit headline derived from opportunity score."""
        pct = round(self.market_opportunity_score * 100)
        return f"{pct}% opportunity"


@dataclass
class ViewState:
    """Serializable map camera position, decoupled from pydeck."""

    latitude: float
    longitude: float
    zoom: float


@dataclass
class CollectionOutcome:
    """Result of a data-collection run (wraps ``run_collection`` output).

    Attributes:
        ok: Per-source success entries (``source``, ``records``, ``path`` …).
        warn: Per-source warnings/failures (``source``, ``error``).
        available_sources: Which sources were configured at collection time.
    """

    ok: list[dict[str, object]]
    warn: list[dict[str, object]]
    available_sources: dict[str, bool]

    @property
    def total_records(self) -> int:
        """Sum of records collected across all successful sources."""
        return sum(int(entry.get("records", 0) or 0) for entry in self.ok)


@dataclass
class AnalysisResult:
    """Full result of one analysis run, cached in Streamlit session state.

    ``recommendations`` holds *all* computed rows (up to the requested cap);
    the UI slices it for the "Top 3 / Show more" behaviour so the map and the
    result list can be kept in sync from a single source of truth.
    """

    params: AnalysisParams
    recommendations: list[Recommendation]
    view_state: ViewState
    generated_at: datetime
    backend_meta: dict[str, object] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when the backend produced no observed-supported routes."""
        return not self.recommendations
