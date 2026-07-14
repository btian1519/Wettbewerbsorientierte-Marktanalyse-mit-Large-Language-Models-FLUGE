"""Typed records returned by connectors (raw, source-shaped data).

Connectors validate/parse external payloads into these Pydantic models; the
normalization layer then maps them onto the ORM observation models. Keeping raw
records separate from ORM rows means a change in an API's response shape only
touches the connector + these models, never the database.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawFlightSchedule(BaseModel):
    """A scheduled service (supply) — e.g. from AirLabs routes/schedules."""

    airline_iata: str
    flight_number: str | None = None
    origin_iata: str
    dest_iata: str
    frequency: int | None = None            # flights per week if known
    days: list[int] = Field(default_factory=list)  # 1=Mon .. 7=Sun
    aircraft_type: str | None = None
    source: str = "airlabs"
    fetched_at: datetime = Field(default_factory=_utcnow)


class RawFlightObservation(BaseModel):
    """An actually observed flight (OpenSky) — used for validation/calibration."""

    callsign: str | None = None
    origin_iata: str | None = None
    dest_iata: str | None = None
    aircraft: str | None = None
    icao24: str | None = None
    observed_at: datetime = Field(default_factory=_utcnow)
    source: str = "opensky"


class RawPassengerStat(BaseModel):
    """Reference passenger statistics (Eurostat) for demand calibration."""

    airport_iata: str | None = None
    origin_iata: str | None = None
    dest_iata: str | None = None
    period: str                              # e.g. "2025" or "2025-M06"
    passengers: float
    source: str = "eurostat"


class RawTrendPoint(BaseModel):
    """A single demand-proxy reading (e.g. Google Trends)."""

    keyword: str
    week: str
    value: float
    timeframe: str | None = None
    source: str = "google_trends"
    fetched_at: datetime = Field(default_factory=_utcnow)


class AirportMetadata(BaseModel):
    """Airport master-data enrichment (OpenFlights / AirLabs)."""

    iata: str
    name: str | None = None
    city: str | None = None
    country: str | None = None
    continent: str | None = None
    lat: float | None = None
    lon: float | None = None
    source: str = "openflights"


class AircraftInfo(BaseModel):
    """Aircraft type → seat capacity (aircraft database)."""

    type_code: str
    seats: int | None = None
    source: str = "aircraft_db"
