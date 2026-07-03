"""Sidebar and shared input controls.

The same three inputs (Airline, Continent, Task) appear on the start page and,
on the results page, inside the sidebar together with an extensible
"Additional Filters" placeholder and a Refresh button. All controls are bound
to the widget keys defined in :mod:`ui.state`, so selections persist across
reruns and are read back through ``state.current_inputs()``.
"""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from services.analysis_service import (
    get_airline_options,
    get_continent_options,
    get_task_options,
)
from ui import state


def render_input_controls(*, container: "st.delta_generator.DeltaGenerator | None" = None) -> None:
    """Render the Airline / Continent / Task selectors.

    Args:
        container: Optional Streamlit container to render into (e.g. the
            sidebar or a column). Defaults to the main area.
    """
    target = container or st

    airline_options = get_airline_options()
    codes = [code for code, _ in airline_options]
    labels = {code: label for code, label in airline_options}

    target.selectbox(
        "Airline",
        options=codes,
        format_func=lambda code: labels[code],
        key=state.Key.IN_AIRLINE,
    )
    target.selectbox(
        "Continent",
        options=get_continent_options(),
        key=state.Key.IN_CONTINENT,
    )
    target.selectbox(
        "Task",
        options=get_task_options(),
        key=state.Key.IN_TASK,
    )


def render_sidebar(on_refresh: Callable[[], None]) -> None:
    """Render the results-page sidebar (inputs + filters + refresh).

    Args:
        on_refresh: Callback invoked when the Refresh button is pressed; it
            should re-run the analysis with the current inputs.
    """
    with st.sidebar:
        st.header("Planning inputs")
        render_input_controls(container=st.sidebar)

        with st.expander("Additional filters", expanded=False):
            _render_additional_filters_placeholder()

        st.divider()
        if st.button("🔄 Refresh", type="primary", use_container_width=True, key="fs_refresh"):
            on_refresh()


def _render_additional_filters_placeholder() -> None:
    """Render the extensible additional-filters placeholder.

    Intentionally inert for now. New filters can be added by appending entries
    here and reading them back via ``state.get_filters()`` in the service call;
    the surrounding layout does not need to change.
    """
    st.caption("Reserved for future filters (aircraft type, distance, demand tier, …).")
    st.session_state.setdefault(state.Key.FILTERS, {})
    st.checkbox("Placeholder filter A", key="fs_filter_a", disabled=True)
    st.checkbox("Placeholder filter B", key="fs_filter_b", disabled=True)
    st.checkbox("Placeholder filter C", key="fs_filter_c", disabled=True)
