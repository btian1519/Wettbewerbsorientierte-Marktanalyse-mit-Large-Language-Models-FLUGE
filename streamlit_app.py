"""FlightScope AI — Streamlit frontend entry point.

Run with::

    streamlit run streamlit_app.py

This module owns only app-level wiring: page config, theme injection, session
state initialisation and routing between the start and results screens. All
data work goes through ``services.analysis_service``; all rendering lives in
``ui/``.
"""

from __future__ import annotations

import streamlit as st

from ui import pages, state, theme
from ui.state import Page


def main() -> None:
    """Configure the page and route to the active screen."""
    st.set_page_config(
        page_title="FlightScope AI",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    theme.inject()
    state.init()

    if state.get_page() is Page.START:
        pages.render_start_page()
    else:
        pages.render_results_page()


if __name__ == "__main__":
    main()
