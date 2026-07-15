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
from frontend.sidebar.diagnostics import refresh_snapshot, summarize_sync_result
from frontend.state import (
    build_request,
    can_undo,
    commit_analysis_snapshot,
    filter_slider,
    inputs_complete,
    mark_net_customized,
    request_clear_filters,
    request_undo,
)
from shared.constants import TOP_VISIBLE_RESULTS
from shared.logging_config import get_logger

log = get_logger("frontend.sidebar")

# Business-friendly tooltip for the Network Availability slider (shown via the
# built-in "?" icon). Deliberately non-technical — no variable names, no maths.
_NET_AVAILABILITY_HELP = (
    "Network Availability reflects how easily existing airline infrastructure and "
    "hubs can support the selected market.\n\n"
    "**100%:** Existing infrastructure and hubs are fully available on the selected "
    "continent. No additional CAPEX is required for new capacity opportunities.\n\n"
    "**0%:** Existing infrastructure and hubs are not available. Additional "
    "investment may be required.\n\n"
    'For "Identify overcapacities", the interpretation is inverted and reflects '
    "potential divestiture flexibility."
)


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
        # Undo restores the entire previously computed analysis (inputs *and*
        # results/map/show-more) from `previous_snapshot`; disabled (greyed out)
        # until at least one Refresh has produced a previous analysis. The actual
        # restore runs at the top of the next rerun (before widgets exist).
        if cundo.button("Undo Changes", use_container_width=True, disabled=not can_undo()):
            request_undo()
            st.rerun()
        if cclear.button("Clear All Filters", use_container_width=True):
            request_clear_filters()
            st.rerun()

        if st.button(
            "REFRESH!", type="primary", use_container_width=True, disabled=not inputs_complete()
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
        # on_change flags a deliberate user value so it survives Task changes /
        # Refresh (see state.sync_network_availability). ``help`` adds the built-in
        # "?" tooltip next to the label — presentation only, no logic change.
        filter_slider(
            "Network Availability", "sl_net",
            on_change=mark_net_customized, help=_NET_AVAILABILITY_HELP,
        )


def _refresh(container: Container) -> None:
    # Optional data sync before recompute (Diagnostics: "Automatically sync data
    # before Refresh"). Off by default → Refresh only recomputes the analysis.
    if st.session_state.get("sync_on_refresh"):
        with st.spinner("Syncing market data before refresh…"):
            results = container.sync_service.sync_market()
        st.session_state["last_sync_results"] = [summarize_sync_result(r) for r in results]
        refresh_snapshot()  # invalidate the cached diagnostics snapshot

    request = build_request()
    analysis = container.analysis_for(st.session_state.get("data_source", "demo"))
    with st.spinner("Recomputing..."):
        st.session_state.response = analysis.analyze(request)
    st.session_state.visible = TOP_VISIBLE_RESULTS
    # Successful Refresh: keep the analysis being replaced as `previous` and record
    # the new one as `current`, enabling a single-level Undo.
    commit_analysis_snapshot(is_refresh=True)
    st.rerun()
