"""World Bank demand connector — slow-moving macro factors (population, GDP).

Open data, no key. Population (``SP.POP.TOTL``) and GDP (``NY.GDP.MKTP.CD``) per
country, refreshed yearly. The HTTP indicator fetch is implemented; per-route
emission is prepared because it needs an IATA→country(ISO) resolution (airport
country data is currently sparse in AIRPORTS.xlsx).
"""

from __future__ import annotations

from ingestion.connectors.base import BaseConnector, ConnectorError, ConnectorStatus
from ingestion.demand.records import RawSignal, RouteContext
from shared.sources import DataSource

_POPULATION = "SP.POP.TOTL"
_GDP = "NY.GDP.MKTP.CD"


class WorldBankConnector(BaseConnector):
    source = DataSource.WORLDBANK
    signal_type = "worldbank"
    base_url = "https://api.worldbank.org/v2"

    def available(self) -> bool:
        return True

    def country_indicator(self, iso2: str, indicator: str) -> float | None:
        """Most-recent value of an indicator for a country (ISO-2 code)."""
        payload = self._get(f"country/{iso2}/indicator/{indicator}", params={"format": "json", "mrv": 1})
        try:
            rows = payload[1]
            return float(rows[0]["value"]) if rows and rows[0].get("value") is not None else None
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ConnectorError(f"worldbank: unexpected payload for {indicator}") from exc

    def fetch(self, ctx: RouteContext, week: str) -> list[RawSignal]:
        # Prepared: resolve endpoint countries → population/GDP signals. Returns
        # empty until IATA→ISO2 resolution is wired (kept out of scope so no
        # country data is invented).
        return []

    def probe(self) -> ConnectorStatus:
        try:
            self.country_indicator("DE", _POPULATION)
            return self.status(reachable=True)
        except Exception:  # noqa: BLE001
            return self.status(reachable=False)
