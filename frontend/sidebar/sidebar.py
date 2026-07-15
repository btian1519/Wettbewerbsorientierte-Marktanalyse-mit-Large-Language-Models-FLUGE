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
from frontend.state import (
    build_request,
    can_undo,
    filter_slider,
    inputs_complete,
    request_clear_filters,
    request_undo,
    save_input_snapshot,
)
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
        # Undo restores ALL inputs to the last computed snapshot; disabled
        # (greyed out) until at least one Refresh has been performed. The actual
        # restore runs at the top of the next rerun (before widgets exist).
        if cundo.button("Undo Changes", use_container_width=True, disabled=not can_undo()):
            request_undo()
            st.rerun()
        if cclear.button("Clear All Filters", use_container_width=True):
            request_clear_filters()
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
        # Keyed sliders: their values live in session_state (sl_margin/net) and are
        # read back by state.current_filter_settings(). Streamlit ignores an
        # externally pre-set session_state value on a widget's *first* render, so
        # filter_slider() passes value= only until the key is established.
        #
        # Only user-friendly labels are shown; internal variable names are hidden.
        # The Distance Efficiency slider is intentionally not rendered (not yet
        # functional). Its value is still consumed by current_filter_settings(),
        # which falls back to the DEFAULT_MIN_DISTANCE_EFFICIENCY default when the
        # widget is absent, so the calculation logic is unchanged and the filter can
        # be re-enabled by restoring the slider here.
        filter_slider("Average Margin", "sl_margin")
        filter_slider("Network Availability", "sl_net")


def _refresh(container: Container) -> None:
    request = build_request()
    analysis = container.analysis_for(st.session_state.get("data_source", "demo"))
    with st.spinner("Recomputing..."):
        st.session_state.response = analysis.analyze(request)
    st.session_state.visible = TOP_VISIBLE_RESULTS
    # Successful Refresh: snapshot all inputs and enable Undo.
    save_input_snapshot(mark_refreshed=True)
    st.rerun()
