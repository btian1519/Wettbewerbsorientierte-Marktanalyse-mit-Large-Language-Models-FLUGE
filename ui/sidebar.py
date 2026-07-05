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
    get_source_status,
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


def render_sidebar(on_refresh: Callable[[], None], on_collect: Callable[[], None]) -> None:
    """Render the results-page sidebar (inputs + filters + data + refresh).

    Args:
        on_refresh: Callback to re-run the analysis with the current inputs.
        on_collect: Callback to collect fresh market data for the current
            region before re-analysing.
    """
    with st.sidebar:
        st.header("Planning inputs")
        render_input_controls(container=st.sidebar)

        with st.expander("Additional filters", expanded=False):
            _render_additional_filters_placeholder()

        with st.expander("Data sources", expanded=False):
            _render_data_sources(on_collect)

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


def _render_data_sources(on_collect: Callable[[], None]) -> None:
    """Show configured-source status and a button to collect fresh data.

    Recommendations require observed market data under ``data/raw``. This
    surfaces which API sources are configured (green) vs. missing credentials
    (grey) and lets the user trigger collection for the selected region.
    """
    status = get_source_status()
    if not status:
        st.caption("Backend/source status unavailable.")
        return

    labels = {
        "airlabs": "AirLabs",
        "aviationstack": "Aviationstack",
        "opensky_flights": "OpenSky history",
        "amadeus": "Amadeus",
        "eurostat": "Eurostat",
        "check24": "Check24",
    }
    for key, label in labels.items():
        icon = "🟢" if status.get(key) else "⚪"
        st.caption(f"{icon} {label}")

    heat_ready = any(status.get(src) for src in ("airlabs", "aviationstack", "opensky_flights"))
    if not heat_ready:
        st.caption(
            "⚠️ No OD-heat source configured. Add an AirLabs / Aviationstack key "
            "or OpenSky OAuth2 credentials to `.env` to get recommendations."
        )

    if st.button("⬇️ Collect data", use_container_width=True, key="fs_collect"):
        on_collect()
