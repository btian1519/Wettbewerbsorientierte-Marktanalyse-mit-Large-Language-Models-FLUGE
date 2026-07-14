"""Eurostat connector — reference passenger statistics for demand calibration.

Docs: https://ec.europa.eu/eurostat/web/main/data/web-services . No API key.
Returns official European airport passenger volumes (dataset ``avia_paoc`` /
``avia_par_*``) used to turn relative demand proxies into absolute passengers.

Prepared: request scaffolding is in place; the JSON-stat parsing for a specific
dataset is left as a focused extension point so the exact indicator/dimensions
can be chosen without touching the connector framework.
"""

from __future__ import annotations

from ingestion.connectors.base import BaseConnector, ConnectorStatus
from ingestion.connectors.records import RawPassengerStat
from shared.sources import DataSource


class EurostatConnector(BaseConnector):
    source = DataSource.EUROSTAT
    base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

    def fetch_airport_passengers(self, dataset: str = "avia_paoc", **filters: str) -> list[RawPassengerStat]:
        """Fetch a JSON-stat cube and flatten it to passenger records.

        Implemented as a prepared seam: the raw request works, but mapping the
        multi-dimensional JSON-stat cube onto (airport, period, passengers)
        requires choosing the concrete dataset dimensions.
        """
        raise NotImplementedError(
            "EurostatConnector.fetch_airport_passengers: JSON-stat parsing is a prepared "
            "extension point. The request layer, auth-free access and record shape are ready."
        )

    def probe(self) -> ConnectorStatus:
        try:
            self._get("avia_paoc", params={"format": "JSON", "geo": "EU27_2020", "sinceTimePeriod": "2023"})
            return self.status(reachable=True)
        except Exception:  # noqa: BLE001 - probe never raises
            return self.status(reachable=False)
