"""Geographic reference data and camera math for the map.

The backend has no airport coordinates, so the frontend provides its own
IATA → (latitude, longitude) lookup. This table covers every airport used in
``src/route_database.ALL_REGION_OD_ROUTES`` and every airline homebase, plus a
few extras seen in the mockups. Unknown codes simply resolve to ``None`` and
are skipped on the map (never raising).

Kept free of Streamlit and pydeck so it stays trivially unit-testable.
"""

from __future__ import annotations

import math

from flightscope_backend.core.constants import REGION_BBOX

from services.models import Coordinate, ViewState

# IATA code -> (latitude, longitude). Approximate airport reference points.
AIRPORT_COORDINATES: dict[str, Coordinate] = {
    # Europe
    "FRA": (50.0379, 8.5622),
    "MUC": (48.3538, 11.7861),
    "LHR": (51.4700, -0.4543),
    "LGW": (51.1537, -0.1821),
    "CDG": (49.0097, 2.5479),
    "AMS": (52.3105, 4.7683),
    "MAD": (40.4936, -3.5668),
    "BCN": (41.2974, 2.0833),
    "FCO": (41.8003, 12.2389),
    "VIE": (48.1103, 16.5697),
    "IST": (41.2753, 28.7519),
    "PMI": (39.5517, 2.7388),
    "CGN": (50.8659, 7.1427),
    # Asia
    "HND": (35.5494, 139.7798),
    "NRT": (35.7719, 140.3929),
    "ICN": (37.4602, 126.4407),
    "HKG": (22.3080, 113.9185),
    "SIN": (1.3644, 103.9915),
    "PVG": (31.1443, 121.8083),
    "PEK": (40.0799, 116.6031),
    "DEL": (28.5562, 77.1000),
    "BOM": (19.0896, 72.8656),
    "BKK": (13.6900, 100.7501),
    "CGK": (-6.1256, 106.6559),
    "KUL": (2.7456, 101.7099),
    # North America
    "JFK": (40.6413, -73.7781),
    "LAX": (33.9416, -118.4085),
    "SFO": (37.6213, -122.3790),
    "ORD": (41.9742, -87.9073),
    "ATL": (33.6407, -84.4277),
    "YYZ": (43.6777, -79.6248),
    "YVR": (49.1967, -123.1815),
    "MEX": (19.4361, -99.0719),
    "CUN": (21.0365, -86.8771),
    "DFW": (32.8998, -97.0403),
    "DAL": (32.8471, -96.8518),
    # South America
    "GRU": (-23.4356, -46.4731),
    "GIG": (-22.8090, -43.2506),
    "BOG": (4.7016, -74.1469),
    "MDE": (6.1645, -75.4231),
    "SCL": (-33.3930, -70.7858),
    "LIM": (-12.0219, -77.1143),
    "EZE": (-34.8222, -58.5358),
    "PTY": (9.0714, -79.3835),
    # Africa
    "CAI": (30.1219, 31.4056),
    "JNB": (-26.1392, 28.2460),
    "NBO": (-1.3192, 36.9278),
    "ADD": (8.9779, 38.7993),
    "CMN": (33.3675, -7.5900),
    "RAK": (31.6069, -8.0363),
    "LOS": (6.5774, 3.3212),
    "ABV": (9.0068, 7.2632),
    # Oceania
    "SYD": (-33.9399, 151.1753),
    "MEL": (-37.6690, 144.8410),
    "BNE": (-27.3842, 153.1175),
    "AKL": (-37.0082, 174.7850),
    "PER": (-31.9385, 115.9672),
}

_MIN_ZOOM = 0.6
_MAX_ZOOM = 4.2


def coord_for(iata: str) -> Coordinate | None:
    """Return ``(lat, lon)`` for an IATA code, or ``None`` if unknown."""
    return AIRPORT_COORDINATES.get(str(iata or "").strip().upper())


def split_od(od: str) -> tuple[str, str]:
    """Split an OD token such as ``"FRA-PMI"`` into ``("FRA", "PMI")``.

    Returns empty strings for malformed input rather than raising.
    """
    parts = str(od or "").split("-")
    if len(parts) != 2:
        return "", ""
    return parts[0].strip().upper(), parts[1].strip().upper()


def midpoint(a: Coordinate, b: Coordinate) -> Coordinate:
    """Return the simple lat/lon midpoint of two coordinates."""
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def bearing_degrees(a: Coordinate, b: Coordinate) -> float:
    """Rough on-screen heading (degrees) from ``a`` to ``b``.

    Uses a flat-plane atan2 of the delta; good enough to orient an aircraft
    glyph along a route line without full great-circle math.
    """
    d_lat = b[0] - a[0]
    d_lon = b[1] - a[1]
    return math.degrees(math.atan2(d_lat, d_lon))


def build_view_state(region: str) -> ViewState:
    """Derive a map camera for a region from its ``REGION_BBOX`` bounding box.

    A specific continent zooms to its bounding box; ``Global`` (or any unknown
    region) yields a world view. Zoom is derived from the larger bbox span.
    """
    bbox = REGION_BBOX.get(region, REGION_BBOX["Global"])
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2.0
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2.0

    lat_span = bbox["lamax"] - bbox["lamin"]
    lon_span = bbox["lomax"] - bbox["lomin"]
    span = max(lat_span, lon_span, 1e-6)
    zoom = math.log2(360.0 / span) - 0.5
    zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, zoom))

    return ViewState(latitude=center_lat, longitude=center_lon, zoom=round(zoom, 2))
