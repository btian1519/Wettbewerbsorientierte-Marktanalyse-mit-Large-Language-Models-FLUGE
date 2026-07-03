"""Recommendation result cards and the show-more / export controls.

Renders the lower main area of the results page: the ranked recommendation
cards (Top 3 initially), each with rank, route, suggestion, benefit, key
metrics, a short rationale and a "Show Details" expander; plus a "Show more"
button that reveals further recommendations (kept in sync with the map through
session state) and an "Export" download.
"""

from __future__ import annotations

import json

import streamlit as st

from services.models import AnalysisResult, Recommendation
from ui import state
from ui.theme import GREEN


def render(result: AnalysisResult) -> None:
    """Render the recommendation list, show-more and export controls."""
    if result.is_empty:
        for warning in result.warnings:
            st.warning(warning)
        return

    visible_count = state.get_visible_count()
    visible = result.recommendations[:visible_count]

    st.subheader("Top recommendations")
    for rec in visible:
        _render_card(rec)

    total = len(result.recommendations)
    col_more, col_export = st.columns(2)
    with col_more:
        if visible_count < total:
            remaining = total - visible_count
            if st.button(f"Show more ({remaining} left)", use_container_width=True, key="fs_show_more"):
                state.reveal_more(total)
                st.rerun()
        else:
            st.button("Show more", use_container_width=True, disabled=True, key="fs_show_more_done")
    with col_export:
        st.download_button(
            "Export",
            data=_export_payload(visible),
            file_name="flightscope_recommendations.json",
            mime="application/json",
            use_container_width=True,
            key="fs_export",
        )


def _render_card(rec: Recommendation) -> None:
    """Render a single recommendation card with its details expander."""
    with st.container(border=True):
        st.markdown('<span class="fs-card-marker"></span>', unsafe_allow_html=True)

        head_rank, head_route, head_focus = st.columns([1, 6, 2], vertical_alignment="center")
        with head_rank:
            st.markdown(f'<div class="fs-rank-badge">{rec.display_rank}</div>', unsafe_allow_html=True)
        with head_route:
            match_pill = (
                '<span class="fs-pill fs-pill--match">TASK&nbsp;MATCH</span>'
                if rec.task_match
                else ""
            )
            st.markdown(
                f'<span class="fs-route">{rec.od}</span> &nbsp; {match_pill}'
                f'<br/><span style="opacity:0.85">{rec.route}</span>',
                unsafe_allow_html=True,
            )
        with head_focus:
            if st.button("📍 Map", key=f"fs_focus_{rec.od}", use_container_width=True):
                state.set_selected_od(rec.od)
                st.rerun()

        sug_col, ben_col = st.columns(2)
        with sug_col:
            st.markdown('<span class="fs-pill">SUGGESTION</span>', unsafe_allow_html=True)
            st.markdown(
                f"Deploy **{rec.aircraft}** · est. **{rec.estimated_pax}** pax/mo",
            )
        with ben_col:
            st.markdown('<span class="fs-pill">BENEFIT</span>', unsafe_allow_html=True)
            st.markdown(
                f"**{rec.benefit_label}** · {rec.market_opportunity_label}",
            )

        _render_kpis(rec)

        with st.expander("Show details"):
            _render_details(rec)


def _render_kpis(rec: Recommendation) -> None:
    """Render the compact key-metric row of a card."""
    k1, k2, k3, k4 = st.columns(4)
    _kpi(k1, "Score", f"{rec.score:.2f}")
    _kpi(k2, "Competitors", str(rec.competitor_count))
    _kpi(k3, "Target flights", str(rec.target_airline_observed_flights))
    _kpi(k4, "Airlines seen", str(rec.observed_airlines_total))


def _kpi(column: "st.delta_generator.DeltaGenerator", label: str, value: str) -> None:
    """Render one label/value KPI cell."""
    column.markdown(
        f'<div class="fs-kpi-label">{label}</div><div class="fs-kpi-value">{value}</div>',
        unsafe_allow_html=True,
    )


def _render_details(rec: Recommendation) -> None:
    """Render the expanded detail block for a recommendation."""
    left, right = st.columns(2)
    with left:
        st.markdown("**Market structure**")
        st.write(
            {
                "Opportunity mode": rec.market_opportunity_label,
                "Opportunity score": round(rec.market_opportunity_score, 3),
                "Target airline present": "YES" if rec.target_airline_present else "NO",
                "Observed airlines": ", ".join(rec.observed_airlines) or "none",
            }
        )
    with right:
        st.markdown("**Operational**")
        st.write(
            {
                "Recommended aircraft": rec.aircraft,
                "Estimated PAX / month": rec.estimated_pax,
                "Origin": f"{rec.origin_name} ({rec.origin_iata})",
                "Destination": f"{rec.dest_name} ({rec.dest_iata})",
            }
        )
    st.markdown("**Rationale**")
    for line in rec.rationale_lines:
        st.caption(line)
    if not rec.has_geometry:
        st.caption("⚠️ No map coordinates for one endpoint — route hidden on map.")


def _export_payload(recs: list[Recommendation]) -> str:
    """Serialise the visible recommendations to a JSON string for download."""
    return json.dumps(
        [
            {
                "rank": rec.display_rank,
                "od": rec.od,
                "route": rec.route,
                "score": rec.score,
                "aircraft": rec.aircraft,
                "estimated_pax": rec.estimated_pax,
                "market_opportunity_label": rec.market_opportunity_label,
                "market_opportunity_score": rec.market_opportunity_score,
                "competitor_count": rec.competitor_count,
                "target_airline_observed_flights": rec.target_airline_observed_flights,
            }
            for rec in recs
        ],
        indent=2,
    )
