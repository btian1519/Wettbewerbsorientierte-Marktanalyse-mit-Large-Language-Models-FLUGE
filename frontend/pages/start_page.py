"""Landing page: title, the three scope inputs and the action button."""

from __future__ import annotations

import streamlit as st

from backend.container import Container
from frontend.components import airline_dropdown, scope_dropdown, task_dropdown
from frontend.state import build_request, go_to, inputs_complete
from shared.constants import TOP_VISIBLE_RESULTS
from shared.logging_config import get_logger

log = get_logger("frontend.start")


def render_start_page(container: Container) -> None:
    st.markdown('<div class="fs-title">FlightScope AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="fs-subtitle">Enter airline and relevant scope:</div>', unsafe_allow_html=True)

    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        airline_dropdown(container.catalog_service)
    with c2:
        scope_dropdown()
    with c3:
        task_dropdown()

    st.write("")
    st.write("")
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("Analyze!", type="primary", use_container_width=True, disabled=not inputs_complete()):
            _run_and_go(container)

    st.markdown(
        '<div class="fs-hint">Preferences can be adapted and specified later...</div>',
        unsafe_allow_html=True,
    )


def _run_and_go(container: Container) -> None:
    request = build_request()
    with st.spinner("Analyzing routes..."):
        st.session_state.response = container.analysis_service.analyze(request)
    st.session_state.visible = TOP_VISIBLE_RESULTS
    go_to("results")
    st.rerun()
