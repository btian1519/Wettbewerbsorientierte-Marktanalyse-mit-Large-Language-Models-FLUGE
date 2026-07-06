"""Pure, dependency-light helper functions (geometry & parsing).

Kept free of any project imports so it is trivially unit-testable and reusable.
"""

from __future__ import annotations

import math
import re
from typing import Iterable

EARTH_RADIUS_KM = 6371.0088

_IATA_IN_PARENS = re.compile(r"\(([A-Z]{3})\)")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (0-360°, 0 = North) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def extract_iata(text: str) -> str | None:
    """Extract a 3-letter IATA code from a string like ``"Munich (MUC)"``."""
    if not text:
        return None
    m = _IATA_IN_PARENS.search(text)
    return m.group(1) if m else None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def format_eur(value: float) -> str:
    """Human-readable EUR amount, e.g. ``1234567 -> '€1.23M'``."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1_000_000:
        return f"{sign}€{v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}€{v / 1_000:.1f}K"
    return f"{sign}€{v:,.0f}"


def format_pax(value: float) -> str:
    """Human-readable passenger count."""
    return f"{value:,.0f}"


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0
