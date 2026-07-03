"""Interactive route map built with pydeck (deck.gl), rendered via Streamlit.

pydeck is chosen for its first-class Streamlit integration (``st.pydeck_chart``)
and its Carto basemap, which needs no Mapbox token. Routes are drawn as arcs,
airports as markers, and an aircraft glyph is placed at each route midpoint.

The aircraft rendering is a *static* glyph deliberately kept behind
``_aircraft_layer`` so it can later be swapped for an animated ``TripsLayer``
without touching the rest of the module. If pydeck is unavailable the map falls
back to a simple table so the page never breaks.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.models import AnalysisResult, Recommendation
from services.geo import bearing_degrees, midpoint
from ui import theme

try:  # pydeck ships with Streamlit but guard anyway.
    import pydeck as pdk

    _PYDECK_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _PYDECK_AVAILABLE = False


def render(result: AnalysisResult, visible: list[Recommendation], selected_od: str | None) -> None:
    """Render the map for the currently visible recommendations.

    Args:
        result: The analysis result (provides the camera / view state).
        visible: The subset of recommendations currently shown in the list;
            the map stays in sync by drawing exactly these.
        selected_od: OD of the recommendation to highlight, if any.
    """
    drawable = [rec for rec in visible if rec.has_geometry]

    if not _PYDECK_AVAILABLE:
        _render_fallback(drawable)
        return

    view = result.view_state
    deck = pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=pdk.ViewState(
            latitude=view.latitude,
            longitude=view.longitude,
            zoom=view.zoom,
            pitch=0,
            bearing=0,
        ),
        layers=[
            _arc_layer(drawable, selected_od),
            _airport_layer(drawable),
            _airport_label_layer(drawable),
            _aircraft_layer(drawable),
        ],
        tooltip={
            "html": "<b>{od}</b><br/>{route}<br/>Score: {score}",
            "style": {"backgroundColor": theme.TEAL_DARK, "color": "white"},
        },
    )
    st.pydeck_chart(deck, use_container_width=True)


# --------------------------------------------------------------------------- #
# Layer builders
# --------------------------------------------------------------------------- #
def _arc_layer(recs: list[Recommendation], selected_od: str | None) -> "pdk.Layer":
    """Curved arc per route; the selected route is highlighted."""
    records: list[dict[str, Any]] = []
    for rec in recs:
        assert rec.origin_coord and rec.dest_coord  # guarded by has_geometry
        highlighted = selected_od is not None and rec.od == selected_od
        records.append(
            {
                "od": rec.od,
                "route": rec.route,
                "score": round(rec.score, 3),
                "source": [rec.origin_coord[1], rec.origin_coord[0]],
                "target": [rec.dest_coord[1], rec.dest_coord[0]],
                "source_color": theme.HIGHLIGHT_RGB if highlighted else theme.ARC_SOURCE_RGB,
                "target_color": theme.HIGHLIGHT_RGB if highlighted else theme.ARC_TARGET_RGB,
                "width": 6 if highlighted else 3,
            }
        )
    return pdk.Layer(
        "ArcLayer",
        data=records,
        get_source_position="source",
        get_target_position="target",
        get_source_color="source_color",
        get_target_color="target_color",
        get_width="width",
        great_circle=True,
        pickable=True,
        auto_highlight=True,
    )


def _airport_layer(recs: list[Recommendation]) -> "pdk.Layer":
    """Scatter markers for every unique airport in the visible routes."""
    return pdk.Layer(
        "ScatterplotLayer",
        data=_unique_airports(recs),
        get_position="position",
        get_fill_color=theme.MARKER_RGB,
        get_radius=1,
        radius_min_pixels=5,
        radius_max_pixels=9,
        pickable=False,
    )


def _airport_label_layer(recs: list[Recommendation]) -> "pdk.Layer":
    """IATA text labels next to each airport marker."""
    return pdk.Layer(
        "TextLayer",
        data=_unique_airports(recs),
        get_position="position",
        get_text="iata",
        get_size=13,
        get_color=theme.LABEL_RGB,
        get_pixel_offset=[0, -12],
        get_alignment_baseline="'bottom'",
    )


def _aircraft_layer(recs: list[Recommendation]) -> "pdk.Layer":
    """Aircraft glyph placed at each route midpoint, oriented along the route.

    Static placeholder. Encapsulated so a later animated ``TripsLayer`` can
    replace it without changes elsewhere.
    """
    records: list[dict[str, Any]] = []
    for rec in recs:
        assert rec.origin_coord and rec.dest_coord
        mid = midpoint(rec.origin_coord, rec.dest_coord)
        records.append(
            {
                "position": [mid[1], mid[0]],
                "text": "✈",  # ✈
                "angle": bearing_degrees(rec.origin_coord, rec.dest_coord),
            }
        )
    return pdk.Layer(
        "TextLayer",
        data=records,
        get_position="position",
        get_text="text",
        get_size=22,
        get_angle="angle",
        get_color=theme.AIRCRAFT_RGB,
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _unique_airports(recs: list[Recommendation]) -> list[dict[str, Any]]:
    """Return one marker record per distinct airport across *recs*."""
    seen: dict[str, dict[str, Any]] = {}
    for rec in recs:
        for iata, coord, name in (
            (rec.origin_iata, rec.origin_coord, rec.origin_name),
            (rec.dest_iata, rec.dest_coord, rec.dest_name),
        ):
            if coord and iata and iata not in seen:
                seen[iata] = {"iata": iata, "name": name, "position": [coord[1], coord[0]]}
    return list(seen.values())


def _render_fallback(recs: list[Recommendation]) -> None:
    """Table fallback when pydeck is not installed."""
    st.info("Map view unavailable (pydeck not installed) — showing route list.")
    st.table(
        [
            {"OD": rec.od, "Route": rec.route, "Score": round(rec.score, 3)}
            for rec in recs
        ]
    )
