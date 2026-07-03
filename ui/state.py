"""Typed Streamlit session-state helpers.

Centralises every session-state key so the rest of the UI never touches raw
string keys. Holds the current page, the last analysis params/result, the
"show more" reveal count, the selected recommendation and the additional-filter
placeholder bucket.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import streamlit as st

from services.analysis_service import (
    DEFAULT_MAX_RECOMMENDATIONS,
    default_effective_month,
    get_airline_options,
    get_continent_options,
    get_task_options,
)
from services.models import AnalysisParams, AnalysisResult

TOP_N_INITIAL = 3
SHOW_MORE_STEP = 3


class Page(str, Enum):
    """The two top-level screens of the app."""

    START = "start"
    RESULTS = "results"


class Key:
    """Namespaced session-state keys."""

    PAGE = "fs_page"
    PARAMS = "fs_params"
    RESULT = "fs_result"
    VISIBLE_COUNT = "fs_visible_count"
    SELECTED_OD = "fs_selected_od"
    FILTERS = "fs_filters"
    # Widget-bound input keys (persist selections across reruns).
    IN_AIRLINE = "fs_in_airline"
    IN_CONTINENT = "fs_in_continent"
    IN_TASK = "fs_in_task"


def init() -> None:
    """Initialise all session-state keys to sensible defaults (idempotent)."""
    ss = st.session_state
    ss.setdefault(Key.PAGE, Page.START.value)
    ss.setdefault(Key.PARAMS, None)
    ss.setdefault(Key.RESULT, None)
    ss.setdefault(Key.VISIBLE_COUNT, TOP_N_INITIAL)
    ss.setdefault(Key.SELECTED_OD, None)
    ss.setdefault(Key.FILTERS, {})
    ss.setdefault(Key.IN_AIRLINE, get_airline_options()[0][0])
    ss.setdefault(Key.IN_CONTINENT, get_continent_options()[0])
    ss.setdefault(Key.IN_TASK, get_task_options()[0])


def get_page() -> Page:
    """Return the current page."""
    return Page(st.session_state[Key.PAGE])


def goto(page: Page) -> None:
    """Switch to *page* on the next rerun."""
    st.session_state[Key.PAGE] = page.value


def current_inputs() -> AnalysisParams:
    """Build :class:`AnalysisParams` from the widget-bound input keys."""
    ss = st.session_state
    return AnalysisParams(
        airline_code=ss[Key.IN_AIRLINE],
        region=ss[Key.IN_CONTINENT],
        task=ss[Key.IN_TASK],
        effective_month=default_effective_month(),
        num_recommendations=DEFAULT_MAX_RECOMMENDATIONS,
    )


def store_result(params: AnalysisParams, result: AnalysisResult) -> None:
    """Persist a fresh analysis result and reset the reveal count / selection."""
    ss = st.session_state
    ss[Key.PARAMS] = params
    ss[Key.RESULT] = result
    ss[Key.VISIBLE_COUNT] = TOP_N_INITIAL
    ss[Key.SELECTED_OD] = None


def get_result() -> AnalysisResult | None:
    """Return the cached analysis result, if any."""
    return st.session_state.get(Key.RESULT)


def get_visible_count() -> int:
    """Return how many recommendations are currently revealed."""
    return int(st.session_state.get(Key.VISIBLE_COUNT, TOP_N_INITIAL))


def reveal_more(total: int) -> None:
    """Increase the reveal count by one step, capped at *total*."""
    current = get_visible_count()
    st.session_state[Key.VISIBLE_COUNT] = min(current + SHOW_MORE_STEP, total)


def get_selected_od() -> str | None:
    """Return the OD of the recommendation focused on the map, if any."""
    return st.session_state.get(Key.SELECTED_OD)


def set_selected_od(od: str | None) -> None:
    """Set (or clear) the map-focused recommendation."""
    st.session_state[Key.SELECTED_OD] = od


def get_filters() -> dict[str, Any]:
    """Return the additional-filters placeholder bucket."""
    return dict(st.session_state.get(Key.FILTERS, {}))
