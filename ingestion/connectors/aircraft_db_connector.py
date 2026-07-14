"""Aircraft database connector — aircraft type → seat capacity.

Supply normalization needs seats-per-flight when a schedule only reports an
aircraft type. This connector provides a small, overridable lookup (typical
single-class-ish seat counts) and a seam to load a fuller external dataset later.
The lookup is generic aircraft data, not project master data.
"""

from __future__ import annotations

from ingestion.connectors.base import BaseConnector, ConnectorStatus
from ingestion.connectors.records import AircraftInfo
from shared.sources import DataSource

# Representative seat counts by ICAO/short type code (extend or load externally).
_DEFAULT_SEATS: dict[str, int] = {
    "A319": 140, "A320": 180, "A321": 220, "A20N": 180, "A21N": 220,
    "A332": 280, "A333": 300, "A343": 290, "A359": 315, "A388": 520,
    "B737": 160, "B738": 189, "B739": 189, "B38M": 189, "B752": 200,
    "B763": 260, "B772": 300, "B77W": 350, "B788": 240, "B789": 290, "B78X": 330,
    "E190": 100, "E195": 120, "CRJ9": 90, "AT76": 78, "DH8D": 78,
}
_DEFAULT_FALLBACK_SEATS = 180


class AircraftDbConnector(BaseConnector):
    source = DataSource.AIRCRAFT_DB
    base_url = ""

    def __init__(self, *args, seat_map: dict[str, int] | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._seats = dict(_DEFAULT_SEATS)
        if seat_map:
            self._seats.update({k.upper(): v for k, v in seat_map.items()})

    def seats_for(self, type_code: str | None) -> int:
        """Best-effort seat count for an aircraft type (fallback for unknowns)."""
        if not type_code:
            return _DEFAULT_FALLBACK_SEATS
        return self._seats.get(type_code.upper(), _DEFAULT_FALLBACK_SEATS)

    def lookup(self, type_code: str) -> AircraftInfo:
        return AircraftInfo(type_code=type_code.upper(), seats=self.seats_for(type_code), source=self.source.value)

    def probe(self) -> ConnectorStatus:
        return self.status(reachable=True)  # local data, always available
