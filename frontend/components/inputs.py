"""The three shared input dropdowns (airline / continent / task).

Reused verbatim on the start page and in the sidebar. They persist through
``st.session_state`` via explicit assignment (no widget keys) so the same widget
can appear on either surface without key collisions, and a chosen value survives
navigation.
"""

from __future__ import annotations

from typing import Sequence

import streamlit as st

from backend.services.catalog_service import CatalogService
from shared.constants import MARKET_SCOPES, TASKS


def _index(options: Sequence[str], value: str | None) -> int | None:
    if value in options:
        return options.index(value)
    return None


def airline_dropdown(catalog: CatalogService) -> None:
    pairs = catalog.airline_options()
    options = [iata for iata, _ in pairs]
    labels = dict(pairs)
    st.session_state.airline = st.selectbox(
        "Airline",
        options,
        index=_index(options, st.session_state.get("airline")),
        placeholder="AIRLINE",
        format_func=lambda i: labels.get(i, i),
        label_visibility="collapsed",
    )


def scope_dropdown() -> None:
    options = list(MARKET_SCOPES)
    st.session_state.scope = st.selectbox(
        "Continent",
        options,
        index=_index(options, st.session_state.get("scope")),
        placeholder="CONTINENT",
        label_visibility="collapsed",
    )


def task_dropdown() -> None:
    options = list(TASKS)
    st.session_state.task = st.selectbox(
        "Task",
        options,
        index=_index(options, st.session_state.get("task")),
        placeholder="Task",
        label_visibility="collapsed",
    )
