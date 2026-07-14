"""Eurostat demand connector — calibration & reference values (no API key).

Primary role is the **calibration layer**: official European airport passenger
statistics that anchor the demand index to absolute passengers. It can also emit a
tourism signal. The JSON-stat request layer is ready; dataset-specific parsing is
a focused seam.
"""

from __future__ import annotations

from ingestion.connectors.base import BaseConnector, ConnectorStatus
from ingestion.demand.records import RawSignal, RouteContext
from shared.sources import DataSource


class EurostatDemandConnector(BaseConnector):
    source = DataSource.EUROSTAT
    signal_type = "eurostat_tourism"
    base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

    def available(self) -> bool:
        return True

    def fetch(self, ctx: RouteContext, week: str) -> list[RawSignal]:
        # Prepared: emit a tourism signal from Eurostat tourism/aviation stats.
        # Returns empty until the concrete dataset dimensions are wired.
        return []

    def reference_passengers(self, airport_iata: str) -> float | None:
        """Annual passengers for an airport (calibration reference). Prepared."""
        raise NotImplementedError(
            "EurostatDemandConnector.reference_passengers: JSON-stat parsing is a prepared "
            "extension point (dataset avia_paoc). The request layer is ready."
        )

    def probe(self) -> ConnectorStatus:
        try:
            self._get("avia_paoc", params={"format": "JSON", "geo": "EU27_2020", "sinceTimePeriod": "2023"})
            return self.status(reachable=True)
        except Exception:  # noqa: BLE001
            return self.status(reachable=False)
