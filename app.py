"""FlightScope AI — Streamlit entry point.

Thin composition + routing layer: it builds the DI container once (cached
resource), ensures the persistent demo database is seeded, and dispatches to the
start or results page. All logic lives in the backend; all rendering in
``frontend``.

Run with::

    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from backend.container import Container, build_container
from frontend.maps import CanvasMapRenderer, MapRenderer
from frontend.pages import render_results_page, render_start_page
from frontend.sidebar import render_sidebar
from frontend.state import apply_pending_action, init_state
from frontend.styles import inject_css


@st.cache_resource(show_spinner="Preparing FlightScope AI (first run seeds the demo database)…")
def _bootstrap() -> tuple[Container, MapRenderer]:
    container = build_container()
    container.data_service.ensure_seeded()  # idempotent; generates only if empty
    return container, CanvasMapRenderer()


def main() -> None:
    st.set_page_config(
        page_title="FlightScope AI",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="auto",
    )
    inject_css()
    init_state()
    apply_pending_action()  # apply queued Undo/Clear before any widget renders
    container, map_renderer = _bootstrap()

    if st.session_state.page == "start":
        render_start_page(container)
    else:
        render_sidebar(container)
        render_results_page(container, map_renderer)


main()
