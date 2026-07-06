"""Collapsible developer / diagnostics footer at the bottom of the sidebar.

Surfaces operational state that is useful during development and demos: tool &
data-source status, the demo/API switch, calculation statistics, map render
options and recent warning/error logs.
"""

from __future__ import annotations

import logging

import streamlit as st

from backend.container import Container
from shared.logging_config import recent_logs


def render_dev_footer(container: Container) -> None:
    with st.expander("🛠  Developer / Diagnostics", expanded=False):
        status = container.data_service.status()
        response = st.session_state.get("response")

        st.markdown("**Tool status**")
        st.write("🟢 Running" if status["seeded"] else "🟠 Not seeded")

        st.markdown("**Input / data source**")
        st.write(f"Ingestion mode: `{status['ingestion_mode']}`")
        source = st.radio(
            "Demo / API switch",
            options=["demo", "api"],
            index=0 if status["ingestion_mode"] == "demo" else 1,
            horizontal=True,
            help="Live API ingestion is prepared via interfaces but not yet enabled.",
        )
        if source == "api":
            st.info("Live API ingestion is not implemented yet — demo data remains active.")

        st.markdown("**Data source status**")
        st.write(
            {
                "airports": status["airports"],
                "airlines": status["airlines"],
                "routes": status["routes"],
                "offers": status["offers"],
                "current_week": status["current_week"],
            }
        )
        with st.container():
            st.caption("Routes by scope")
            st.write(status["routes_by_scope"])

        st.markdown("**Last update**")
        st.write(status["last_updated"])

        st.markdown("**Calculation status**")
        if response is not None:
            st.write(response.stats)
        else:
            st.write("No calculation run yet.")

        st.markdown("**Map rendering options**")
        st.session_state.map_height = st.slider(
            "Map height (px)", min_value=260, max_value=560,
            value=st.session_state.get("map_height", 360), step=20,
        )

        st.markdown("**Error logs** (warnings and above)")
        logs = recent_logs(limit=15, min_level=logging.WARNING)
        st.code("\n".join(logs) if logs else "No warnings or errors.", language="text")

        st.caption(f"DB: {status['db_url']}")
