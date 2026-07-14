"""AirLabs connector — primary supply source (schedules / routes).

Docs: https://airlabs.co/docs/ . Auth is a single ``api_key`` query parameter,
loaded from the environment (never hard-coded). Implements real request/parse
logic; all resilience (retry, rate limit, error handling) comes from
:class:`~ingestion.connectors.base.BaseConnector`.
"""

from __future__ import annotations

from typing import Any

from ingestion.connectors.base import (
    BaseConnector,
    ConnectorError,
    ConnectorStatus,
    QuotaExceededError,
)
from ingestion.connectors.records import RawFlightSchedule
from shared.sources import DataSource

_DAYS = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}


class AirLabsConnector(BaseConnector):
    source = DataSource.AIRLABS
    base_url = "https://airlabs.co/api/v9"

    def is_configured(self) -> bool:
        return bool(self._settings.airlabs_api_key)

    def _auth_params(self) -> dict[str, Any]:
        return {"api_key": self._settings.airlabs_api_key or ""}

    # ------------------------------------------------------------------ #
    def fetch_routes(self, dep_iata: str) -> list[RawFlightSchedule]:
        """Scheduled services departing an airport → supply records."""
        payload = self._get("routes", params={"dep_iata": dep_iata.upper()})
        # AirLabs returns HTTP 200 with an {"error": {...}} body for a restricted
        # endpoint / bad param / exhausted quota — surface that real message.
        if isinstance(payload, dict) and payload.get("error"):
            err = payload["error"]
            msg = str(err.get("message", err) if isinstance(err, dict) else err)
            if "limit" in msg.lower():  # e.g. "The monthly request limit has been exceeded."
                raise QuotaExceededError(f"AirLabs API error: {msg}")
            raise ConnectorError(f"AirLabs API error: {msg}")
        rows = payload.get("response") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            shape = list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
            raise ConnectorError(f"airlabs: unexpected /routes payload (shape={shape}): {str(payload)[:180]}")
        out: list[RawFlightSchedule] = []
        for r in rows:
            rec = self._parse_route(r)
            if rec is not None:
                out.append(rec)
        self._log.info("AirLabs: %d schedules from %s", len(out), dep_iata)
        return out

    def _parse_route(self, r: dict) -> RawFlightSchedule | None:
        dep, arr = r.get("dep_iata"), r.get("arr_iata")
        airline = r.get("airline_iata")
        if not (dep and arr and airline):
            return None  # skip incomplete rows (validation)
        days = [_DAYS[d] for d in (r.get("days") or []) if d in _DAYS]
        return RawFlightSchedule(
            airline_iata=str(airline).upper(),
            flight_number=str(r.get("flight_number")) if r.get("flight_number") else None,
            origin_iata=str(dep).upper(),
            dest_iata=str(arr).upper(),
            frequency=len(days) or None,
            days=days,
            aircraft_type=r.get("aircraft_icao") or None,
            source=self.source.value,
        )

    # ------------------------------------------------------------------ #
    def probe(self) -> ConnectorStatus:
        """Explicit, cheap reachability check (used by the manual footer button)."""
        try:
            self._get("ping")
            return self.status(reachable=True)
        except ConnectorError:
            return self.status(reachable=False)
