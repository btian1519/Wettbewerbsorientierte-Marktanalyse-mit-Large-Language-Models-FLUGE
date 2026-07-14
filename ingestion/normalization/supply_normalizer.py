"""Normalize scheduled services (AirLabs) into supply observations.

Aggregates all flight numbers of a carrier on a route into one weekly capacity
row: weekly frequency = Σ days-per-week, weekly seats = Σ (frequency × seats),
where seats come from the aircraft type via a ``seats_for`` callback.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Callable, Sequence

from ingestion.connectors.records import RawFlightSchedule


def normalize_schedules(
    schedules: Sequence[RawFlightSchedule],
    *,
    week: str,
    snapshot_date: date,
    resolve_route_id: Callable[[str, str], int],
    seats_for: Callable[[str | None], int],
    source: str = "airlabs",
) -> list[dict]:
    """Return SupplyObservation-shaped dicts, one per (route, airline)."""
    # Group by (origin, dest, airline).
    grouped: dict[tuple[str, str, str], list[RawFlightSchedule]] = {}
    for s in schedules:
        grouped.setdefault((s.origin_iata, s.dest_iata, s.airline_iata), []).append(s)

    rows: list[dict] = []
    for (origin, dest, airline), items in grouped.items():
        frequency = 0
        seats_total = 0
        aircraft_counter: Counter[str] = Counter()
        for s in items:
            freq = s.frequency or (len(s.days) or 1)
            frequency += freq
            seats_total += freq * seats_for(s.aircraft_type)
            if s.aircraft_type:
                aircraft_counter[s.aircraft_type] += freq
        rows.append(
            {
                "route_id": resolve_route_id(origin, dest),
                "airline_iata": airline,
                "week": week,
                "snapshot_date": snapshot_date,
                "available_seats": int(seats_total),
                "frequency": int(frequency),
                "aircraft_type": aircraft_counter.most_common(1)[0][0] if aircraft_counter else None,
                "average_price": None,  # AirLabs provides no fares; filled by Amadeus later
                "flight_number": None,
                "source": source,
            }
        )
    return rows
