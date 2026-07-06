"""Sidebar renderer.

Re-exposes every start-page input (no back button, per the brief), the collapsed
'Additional Filters' section and the Refresh / Undo / Clear actions, followed by
the dev footer. All sections start collapsed so the sidebar fits without
scrolling.
"""

from __future__ import annotations

import streamlit as st

from backend.container import Container
from frontend.components import airline_dropdown, scope_dropdown, task_dropdown
from frontend.sidebar.dev_footer import render_dev_footer
from frontend.state import build_request, inputs_complete, reset_filters
from shared.constants import TOP_VISIBLE_RESULTS
from shared.logging_config import get_logger

log = get_logger("frontend.sidebar")


def render_sidebar(container: Container) -> None:
    with st.sidebar:
        st.markdown('<div class="fs-side-title">FlightScope AI</div>', unsafe_allow_html=True)

        # --- Editable scope inputs (mirror the start page) --------------
        airline_dropdown(container.catalog_service)
        scope_dropdown()
        task_dropdown()

        # --- Additional Filters (collapsed) ----------------------------
        _render_filters()

        # --- Actions ---------------------------------------------------
        cundo, cclear = st.columns(2)
        if cundo.button("Undo Changes", use_container_width=True):
            st.session_state.filters = dict(st.session_state.filters_committed)
            st.rerun()
        if cclear.button("Clear All Filters", use_container_width=True):
            reset_filters()
            st.rerun()

        if st.button(
            "REFRESH", type="primary", use_container_width=True, disabled=not inputs_complete()
        ):
            _refresh(container)

        st.write("")
        # --- Dev footer (bottom) ---------------------------------------
        render_dev_footer(container)


def _render_filters() -> None:
    with st.expander("Additional Filters", expanded=False):
        f = st.session_state.filters
        margin = st.slider(
            "Average Margin — Marge_average", 0, 100,
            int(round(f["marge_average"] * 100)), format="%d%%",
        )
        net = st.slider(
            "Network Availability — Network_availability", 0, 100,
            int(round(f["network_availability"] * 100)), format="%d%%",
        )
        dist = st.slider(
            "Distance Efficiency — distance_efficiency (min)", 0, 100,
            int(round(f["min_distance_efficiency"] * 100)), format="%d%%",
        )
        st.caption("Further filter variables can be plugged in here (placeholder).")
        st.session_state.filters = {
            "marge_average": margin / 100.0,
            "network_availability": net / 100.0,
            "min_distance_efficiency": dist / 100.0,
        }


def _refresh(container: Container) -> None:
    request = build_request()
    with st.spinner("Recomputing..."):
        st.session_state.response = container.analysis_service.analyze(request)
    st.session_state.visible = TOP_VISIBLE_RESULTS
    st.session_state.filters_committed = dict(st.session_state.filters)
    st.rerun()
