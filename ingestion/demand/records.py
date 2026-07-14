"""Typed records for the demand pipeline (Pydantic).

Separate from the ORM rows so a source's response shape or the internal model can
change without touching the database. ``WeeklyDemand`` is the *only* shape the
analysis engine ever sees (via ``get_weekly_demand``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

# The demand-index components, in priority order (drives weights & scores).
SIGNAL_COMPONENTS = ("google", "wikipedia", "tourism", "population", "gdp", "event")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RouteContext(BaseModel):
    """Everything a connector needs to build queries for one O-D route."""

    origin_iata: str
    dest_iata: str
    origin_city: str | None = None
    dest_city: str | None = None


class RawSignal(BaseModel):
    """A single raw demand signal, as produced by a connector."""

    origin_airport: str
    destination_airport: str
    signal_type: str            # google_trends | wikipedia_views | eurostat_passengers | worldbank_gdp | ...
    signal_value: float
    search_term: str | None = None
    source: str
    week: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)


class DemandSignals(BaseModel):
    """Normalized (0..100) component scores for one route/week. ``None`` = missing."""

    google: float | None = None
    wikipedia: float | None = None
    tourism: float | None = None
    population: float | None = None
    gdp: float | None = None
    event: float | None = None

    def present(self) -> dict[str, float]:
        return {c: getattr(self, c) for c in SIGNAL_COMPONENTS if getattr(self, c) is not None}


class DemandComputation(BaseModel):
    """Output of the demand model (index + base confidence, fully transparent)."""

    demand_index: float                 # 0..100
    weight_coverage: float              # fraction of full weight present (0..1)
    weights_used: dict[str, float]
    calculation_version: str


class WeeklyDemand(BaseModel):
    """The demand contract exposed to the analysis engine."""

    origin: str
    destination: str
    week: str
    estimated_weekly_passengers: float
    demand_index: float
    confidence_score: float
