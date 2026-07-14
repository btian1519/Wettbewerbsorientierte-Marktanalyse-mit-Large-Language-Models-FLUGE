"""OpenFlights connector — airport & route metadata (no API key).

Source: the public ``airports.dat`` / ``routes.dat`` CSVs. Enriches airport
master data (city, country, coordinates) *without overwriting* existing rows —
the normalization/ingestion layer only fills gaps.
"""

from __future__ import annotations

import csv
import io

from ingestion.connectors.base import BaseConnector, ConnectorError, ConnectorStatus
from ingestion.connectors.records import AirportMetadata
from shared.sources import DataSource

_AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"


class OpenFlightsConnector(BaseConnector):
    source = DataSource.OPENFLIGHTS
    base_url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"

    def fetch_airports(self) -> list[AirportMetadata]:
        """Download and parse the OpenFlights airport database."""
        try:
            resp = self._session.get(_AIRPORTS_URL, timeout=self.timeout_s)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise ConnectorError(f"openflights: download failed: {exc}") from exc

        out: list[AirportMetadata] = []
        reader = csv.reader(io.StringIO(resp.text))
        for row in reader:
            # Columns: id,name,city,country,IATA,ICAO,lat,lon,...
            if len(row) < 8:
                continue
            iata = row[4].strip()
            if not iata or iata == "\\N" or len(iata) != 3:
                continue
            try:
                lat, lon = float(row[6]), float(row[7])
            except ValueError:
                continue
            out.append(
                AirportMetadata(
                    iata=iata.upper(),
                    name=row[1].strip() or None,
                    city=row[2].strip() or None,
                    country=row[3].strip() or None,
                    lat=lat,
                    lon=lon,
                    source=self.source.value,
                )
            )
        self._log.info("OpenFlights: parsed %d airports", len(out))
        return out

    def probe(self) -> ConnectorStatus:
        try:
            resp = self._session.head(_AIRPORTS_URL, timeout=self.timeout_s)
            return self.status(reachable=resp.status_code < 400)
        except Exception:  # noqa: BLE001
            return self.status(reachable=False)
