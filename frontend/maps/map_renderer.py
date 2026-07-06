"""Map renderer abstraction + the Canvas implementation.

The :class:`MapRenderer` Protocol is the seam that keeps the map engine
swappable — a future PyDeck/deck.gl renderer only has to satisfy the same
``render`` signature. :class:`CanvasMapRenderer` prepares the payload (view
bounding box, bbox-culled country polygons, route endpoints) and hands it to the
self-contained HTML/JS component.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np
import streamlit.components.v1 as components

from backend.dto import RouteResult
from database.repository.interfaces import AirportRead
from frontend.maps.map_html import build_map_html
from frontend.theme import COLORS
from shared.config import get_settings
from shared.constants import INTERCONTINENTAL

_WORLD_VIEW = {"minLon": -170.0, "maxLon": 190.0, "minLat": -58.0, "maxLat": 82.0}


class MapRenderer(Protocol):
    def render(
        self,
        scope: str,
        scope_airports: Sequence[AirportRead],
        routes: Sequence[RouteResult],
        height: int = 360,
    ) -> None: ...


@lru_cache(maxsize=1)
def _load_world() -> tuple[dict, list[tuple[float, float, float, float]]]:
    path = get_settings().data_dir.parent / "assets" / "world_countries.json"
    geo = json.loads(Path(path).read_text(encoding="utf-8"))
    bboxes: list[tuple[float, float, float, float]] = []
    for f in geo["features"]:
        xs: list[float] = []
        ys: list[float] = []
        for poly in f["geometry"]["coordinates"]:
            for ring in poly:
                for x, y in ring:
                    xs.append(x)
                    ys.append(y)
        bboxes.append((min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0))
    return geo, bboxes


def _bbox_of(points: Sequence[tuple[float, float]], must_include: Sequence[tuple[float, float]] = ()) -> dict:
    """Robust bounding box.

    Uses the 2nd/98th percentiles so that a handful of mislabelled airports in
    the source data (continent label not matching the coordinates) cannot blow up
    the continent zoom. Any coordinates in ``must_include`` (the visible route
    endpoints) are always kept inside the view so planes never fly off-canvas.
    """
    lons = np.array([p[0] for p in points], dtype=float)
    lats = np.array([p[1] for p in points], dtype=float)
    lo_lon, hi_lon = np.percentile(lons, [2, 98])
    lo_lat, hi_lat = np.percentile(lats, [2, 98])
    for mlon, mlat in must_include:
        lo_lon, hi_lon = min(lo_lon, mlon), max(hi_lon, mlon)
        lo_lat, hi_lat = min(lo_lat, mlat), max(hi_lat, mlat)
    dlon = (hi_lon - lo_lon) or 10.0
    dlat = (hi_lat - lo_lat) or 10.0
    padx, pady = dlon * 0.08, dlat * 0.12
    return {
        "minLon": float(lo_lon - padx),
        "maxLon": float(hi_lon + padx),
        "minLat": float(lo_lat - pady),
        "maxLat": float(hi_lat + pady),
    }


def _intersects(a: tuple[float, float, float, float], v: dict) -> bool:
    return not (a[2] < v["minLon"] or a[0] > v["maxLon"] or a[3] < v["minLat"] or a[1] > v["maxLat"])


class CanvasMapRenderer:
    """Frame-based airplane animation on an HTML5 Canvas (offline capable)."""

    def render(
        self,
        scope: str,
        scope_airports: Sequence[AirportRead],
        routes: Sequence[RouteResult],
        height: int = 360,
    ) -> None:
        geo, bboxes = _load_world()

        endpoints = [(r.origin_lon, r.origin_lat) for r in routes] + [
            (r.dest_lon, r.dest_lat) for r in routes
        ]
        if scope == INTERCONTINENTAL or not scope_airports:
            view = dict(_WORLD_VIEW)
        else:
            view = _bbox_of([(a.lon, a.lat) for a in scope_airports], must_include=endpoints)

        features = [f for f, bb in zip(geo["features"], bboxes) if _intersects(bb, view)]

        payload = {
            "colors": COLORS,
            "height": height,
            "view": view,
            "geojson": {"type": "FeatureCollection", "features": features},
            "airports": [[a.lon, a.lat] for a in scope_airports],
            "routes": [
                {"o": [r.origin_lon, r.origin_lat], "d": [r.dest_lon, r.dest_lat], "rank": r.rank}
                for r in routes
            ],
            "activeCountries": [],
        }
        components.html(build_map_html(payload), height=height + 6, scrolling=False)
