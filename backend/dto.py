"""Data-transfer objects that cross the frontend/backend boundary.

Inputs (``FilterSettings``, ``AnalysisRequest``) are Pydantic models so the UI
gets validation for free. Outputs (``RouteResult``, ``AnalysisResponse``) are
frozen dataclasses — cheap to create in bulk and easy to serialise for export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from shared.constants import (
    DEFAULT_MARGE_AVERAGE,
    DEFAULT_MIN_DISTANCE_EFFICIENCY,
    DEFAULT_NETWORK_AVAILABILITY,
    GAP_LABEL_OVERCAPACITY,
    Task,
)


class FilterSettings(BaseModel):
    """Tunable analysis parameters exposed as the sidebar 'Additional Filters'.

    ``marge_average`` feeds the benefit formula directly. ``network_availability``
    holds the slider fraction ``x`` (0..1); the engine converts it into the
    direction-dependent factor ``F`` per route (see
    :func:`backend.analysis.engine.network_availability_factor`).
    ``min_distance_efficiency`` is a threshold that drops routes whose computed
    distance efficiency is below it. ``extra`` reserves room for future filter
    variables without a schema change.
    """

    marge_average: float = Field(DEFAULT_MARGE_AVERAGE, ge=0.0, le=1.0)
    network_availability: float = Field(DEFAULT_NETWORK_AVAILABILITY, ge=0.0, le=1.0)
    min_distance_efficiency: float = Field(DEFAULT_MIN_DISTANCE_EFFICIENCY, ge=0.0, le=1.0)
    extra: dict[str, float] = Field(default_factory=dict)


class AnalysisRequest(BaseModel):
    airline_iata: str
    scope: str
    task: Task
    filters: FilterSettings = Field(default_factory=FilterSettings)
    week: str | None = None


@dataclass(frozen=True, slots=True)
class RouteResult:
    rank: int
    origin_iata: str
    dest_iata: str
    origin_name: str | None
    dest_name: str | None
    origin_city: str | None
    dest_city: str | None
    origin_country: str | None
    dest_country: str | None
    origin_continent: str
    dest_continent: str
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    distance_km: float
    demand: float
    total_supply: float
    delta_pax: float           # airline-attributed for overcapacity mode
    benefit_eur: float         # airline-attributed for overcapacity mode
    avg_price_eur: float
    price_source: str
    num_airlines: int          # active carriers on the route (count only)
    selected_airline_share: float  # supply share of the selected airline (0..1)
    gap_label: str             # "Market Gap" or "Overcapacities"

    @property
    def is_overcapacity(self) -> bool:
        return self.gap_label == GAP_LABEL_OVERCAPACITY

    @property
    def display_benefit(self) -> float:
        """Benefit for presentation: absolute value in overcapacity mode.

        Internally ``benefit_eur`` stays signed (negative for overcapacity) so
        ranking is unaffected; only the displayed figure uses ``abs``.
        """
        return abs(self.benefit_eur) if self.is_overcapacity else self.benefit_eur

    @property
    def display_delta(self) -> float:
        """Delta/overcapacity for presentation: absolute value in overcapacity mode."""
        return abs(self.delta_pax) if self.is_overcapacity else self.delta_pax


@dataclass(frozen=True, slots=True)
class AnalysisResponse:
    task: Task
    scope: str
    airline_iata: str
    week: str
    results: list[RouteResult]
    stats: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def title(self) -> str:
        return (
            "Explore new opportunities:"
            if self.task == Task.OPPORTUNITIES
            else "Reduce current overcapacities:"
        )
