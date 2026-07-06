"""Session-state helpers.

Encapsulates all ``st.session_state`` keys behind named functions so pages never
touch raw string keys and the state schema is documented in one place.
"""

from __future__ import annotations

import streamlit as st

from backend.dto import AnalysisRequest, FilterSettings
from shared.constants import (
    DEFAULT_MARGE_AVERAGE,
    DEFAULT_MIN_DISTANCE_EFFICIENCY,
    DEFAULT_NETWORK_AVAILABILITY,
    TOP_VISIBLE_RESULTS,
    Task,
)

_DEFAULT_FILTERS = {
    "marge_average": DEFAULT_MARGE_AVERAGE,
    "network_availability": DEFAULT_NETWORK_AVAILABILITY,
    "min_distance_efficiency": DEFAULT_MIN_DISTANCE_EFFICIENCY,
}


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("page", "start")
    ss.setdefault("airline", None)
    ss.setdefault("scope", None)
    ss.setdefault("task", None)
    ss.setdefault("filters", dict(_DEFAULT_FILTERS))
    ss.setdefault("filters_committed", dict(_DEFAULT_FILTERS))
    ss.setdefault("visible", TOP_VISIBLE_RESULTS)
    ss.setdefault("response", None)


def go_to(page: str) -> None:
    st.session_state.page = page


def reset_filters() -> None:
    st.session_state.filters = dict(_DEFAULT_FILTERS)


def current_filter_settings() -> FilterSettings:
    f = st.session_state.filters
    return FilterSettings(
        marge_average=f["marge_average"],
        network_availability=f["network_availability"],
        min_distance_efficiency=f["min_distance_efficiency"],
    )


def build_request() -> AnalysisRequest:
    ss = st.session_state
    return AnalysisRequest(
        airline_iata=ss.airline,
        scope=ss.scope,
        task=Task(ss.task),
        filters=current_filter_settings(),
    )


def inputs_complete() -> bool:
    ss = st.session_state
    return bool(ss.airline and ss.scope and ss.task)
