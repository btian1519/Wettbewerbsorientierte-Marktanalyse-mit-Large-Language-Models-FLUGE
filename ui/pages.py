"""Start page and results page composition.

Ties the UI components together and owns the (thin) control flow: running the
analysis via the service layer with a progress indicator, and switching between
the start and results screens. No business logic lives here.
"""

from __future__ import annotations

import streamlit as st

from services.analysis_service import run_analysis
from services.models import AnalysisParams
from ui import map as map_view
from ui import results as results_view
from ui import sidebar, state
from ui.state import Page


def render_start_page() -> None:
    """Render the landing screen: title and the three inputs plus GO."""
    st.markdown('<div class="fs-title">FlightScope AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="fs-subtitle">Enter airline and relevant scope</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        sidebar.render_input_controls(container=center)
        st.write("")
        if st.button("GO !", type="primary", use_container_width=True, key="fs_go"):
            _run_and_open_results(state.current_inputs())
        st.markdown(
            '<div class="fs-hint">Preferences can be adapted and specified later…</div>',
            unsafe_allow_html=True,
        )


def render_results_page() -> None:
    """Render the results screen: sidebar + map (top) + recommendations (bottom)."""
    sidebar.render_sidebar(on_refresh=lambda: _run_and_open_results(state.current_inputs()))

    result = state.get_result()
    if result is None:
        st.info("No analysis yet. Set your inputs in the sidebar and press Refresh.")
        return

    if result.backend_meta.get("runtime_context"):
        st.caption(str(result.backend_meta["runtime_context"]))

    visible = result.recommendations[: state.get_visible_count()]
    map_view.render(result, visible, state.get_selected_od())
    results_view.render(result)


def _run_and_open_results(params: AnalysisParams) -> None:
    """Run the analysis with a progress indicator and open the results page."""
    with st.spinner("Running analysis…"):
        try:
            result = run_analysis(params)
        except RuntimeError as exc:
            st.error(str(exc))
            return
    state.store_result(params, result)
    state.goto(Page.RESULTS)
    st.rerun()
