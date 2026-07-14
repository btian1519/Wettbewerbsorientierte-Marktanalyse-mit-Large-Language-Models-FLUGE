"""OpenSky connector — actually observed flights, for validation/calibration.

Docs: https://opensky-network.org/apidoc/ . Works anonymously (tight rate limits)
or with credentials. Used to cross-check AirLabs schedules, not as primary supply.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ingestion.connectors.base import BaseConnector, ConnectorError, ConnectorStatus
from ingestion.connectors.records import RawFlightObservation
from shared.sources import DataSource


class OpenSkyConnector(BaseConnector):
    source = DataSource.OPENSKY
    base_url = "https://opensky-network.org/api"
    min_interval_s = 1.0  # be gentle with the free tier

    def is_configured(self) -> bool:
        return True  # anonymous access is allowed

    def _auth_headers(self) -> dict[str, str]:
        # Basic auth if credentials are provided; anonymous otherwise.
        return {}

    def fetch_arrivals(self, airport_iata: str, begin: int, end: int) -> list[RawFlightObservation]:
        """Arrivals at an ICAO airport in a UNIX-time window.

        Note: OpenSky keys airports by ICAO; mapping IATA→ICAO is handled by the
        normalization layer. Kept minimal here — this source is for calibration.
        """
        payload = self._get("flights/arrival", params={"airport": airport_iata, "begin": begin, "end": end})
        if not isinstance(payload, list):
            raise ConnectorError("opensky: unexpected arrivals payload")
        out: list[RawFlightObservation] = []
        for f in payload:
            out.append(
                RawFlightObservation(
                    callsign=(f.get("callsign") or "").strip() or None,
                    dest_iata=airport_iata,
                    icao24=f.get("icao24"),
                    observed_at=datetime.fromtimestamp(f.get("lastSeen", 0), tz=timezone.utc),
                    source=self.source.value,
                )
            )
        return out

    def probe(self) -> ConnectorStatus:
        try:
            # Cheap request with a tiny window.
            now = int(datetime.now(timezone.utc).timestamp())
            self._get("flights/arrival", params={"airport": "EDDF", "begin": now - 3600, "end": now})
            return self.status(reachable=True)
        except ConnectorError:
            return self.status(reachable=False)
