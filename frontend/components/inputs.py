"""The three shared input dropdowns (airline / continent / task).

Reused verbatim on the start page and in the sidebar so both surfaces look and
behave identically. The widgets are **keyed** (``airline`` / ``scope`` / ``task``)
so their state lives in ``st.session_state`` and can be restored programmatically
(Undo). ``index=None`` + ``placeholder`` gives the empty initial state; the fields
are made non-editable (pick-only, no typing/search) via CSS in
:mod:`frontend.styles`.
"""

from __future__ import annotations

import streamlit as st

from backend.services.catalog_service import CatalogService
from shared.constants import MARKET_SCOPES, TASKS


def airline_dropdown(catalog: CatalogService) -> None:
    pairs = catalog.airline_options()
    labels = dict(pairs)
    st.selectbox(
        "Airline",
        [iata for iata, _ in pairs],
        key="airline",
        index=None,
        placeholder="AIRLINE",
        format_func=lambda i: labels.get(i, i),
        label_visibility="collapsed",
    )


def scope_dropdown() -> None:
    st.selectbox(
        "Continent",
        list(MARKET_SCOPES),
        key="scope",
        index=None,
        placeholder="CONTINENT",
        label_visibility="collapsed",
    )


def task_dropdown() -> None:
    st.selectbox(
        "Task",
        list(TASKS),
        key="task",
        index=None,
        placeholder="Task",
        label_visibility="collapsed",
    )
