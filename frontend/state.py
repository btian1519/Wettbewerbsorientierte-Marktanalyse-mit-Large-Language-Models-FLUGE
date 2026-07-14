"""Session-state helpers.

Encapsulates all ``st.session_state`` keys behind named functions so pages never
touch raw string keys and the state schema is documented in one place.

Inputs are **keyed** widgets (``airline``/``scope``/``task`` and the slider keys
``sl_margin``/``sl_net``/``sl_dist``). Because a keyed widget's value cannot be
mutated after the widget is instantiated in the same run, Undo/Clear register a
*pending action* and :func:`apply_pending_action` applies it at the very top of
the next run — before any widget is created.

Streamlit quirk (important): an externally pre-set ``session_state`` value is
ignored on a widget's **first** instantiation — only ``value=`` is honoured then.
So the sliders are *not* seeded in ``init_state``; :func:`filter_slider` passes
``value=`` on the first render and lets ``session_state`` drive it afterwards
(which is also what lets Undo/Clear set the value on later renders).
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

# Slider keys hold integer percentages; converted to 0..1 for the model.
_DEFAULT_SLIDERS = {
    "sl_margin": int(round(DEFAULT_MARGE_AVERAGE * 100)),
    "sl_net": int(round(DEFAULT_NETWORK_AVAILABILITY * 100)),
    "sl_dist": int(round(DEFAULT_MIN_DISTANCE_EFFICIENCY * 100)),
}
_INPUT_KEYS = ("airline", "scope", "task", *_DEFAULT_SLIDERS.keys())
# Fallback values when snapshotting inputs before the widgets have rendered.
_SNAPSHOT_DEFAULTS = {"airline": None, "scope": None, "task": None, **_DEFAULT_SLIDERS}


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("page", "start")
    ss.setdefault("visible", TOP_VISIBLE_RESULTS)
    ss.setdefault("response", None)
    # Undo support.
    ss.setdefault("input_snapshot", None)
    ss.setdefault("has_refreshed", False)
    ss.setdefault("_pending_action", None)
    # NB: slider keys (sl_margin/net/dist) are intentionally NOT seeded here —
    # see the module docstring; filter_slider() supplies the first-render default.


def go_to(page: str) -> None:
    st.session_state.page = page


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #
def filter_slider(label: str, key: str) -> None:
    """Render a 0–100% filter slider that shows its default on first render.

    ``value=`` is supplied only until the key exists in ``session_state``;
    thereafter the widget (and Undo/Clear, which set ``session_state[key]`` before
    the widget) drive it. This works around Streamlit ignoring an externally
    pre-set value on a widget's first instantiation.
    """
    kwargs = {} if key in st.session_state else {"value": _DEFAULT_SLIDERS[key]}
    st.slider(label, 0, 100, key=key, format="%d%%", **kwargs)


def current_filter_settings() -> FilterSettings:
    ss = st.session_state
    return FilterSettings(
        marge_average=ss.get("sl_margin", _DEFAULT_SLIDERS["sl_margin"]) / 100.0,
        network_availability=ss.get("sl_net", _DEFAULT_SLIDERS["sl_net"]) / 100.0,
        min_distance_efficiency=ss.get("sl_dist", _DEFAULT_SLIDERS["sl_dist"]) / 100.0,
    )


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
def build_request() -> AnalysisRequest:
    ss = st.session_state
    return AnalysisRequest(
        airline_iata=ss.get("airline"),
        scope=ss.get("scope"),
        task=Task(ss.get("task")),
        filters=current_filter_settings(),
    )


def inputs_complete() -> bool:
    ss = st.session_state
    return bool(ss.get("airline") and ss.get("scope") and ss.get("task"))


# --------------------------------------------------------------------------- #
# Undo snapshot + pending actions
# --------------------------------------------------------------------------- #
def save_input_snapshot(*, mark_refreshed: bool) -> None:
    """Snapshot the complete input state after a successful computation.

    ``mark_refreshed`` is False for the initial Analyze (Undo stays disabled) and
    True for every Refresh (Undo becomes enabled).
    """
    ss = st.session_state
    ss.input_snapshot = {k: ss.get(k, _SNAPSHOT_DEFAULTS[k]) for k in _INPUT_KEYS}
    if mark_refreshed:
        ss.has_refreshed = True


def can_undo() -> bool:
    return bool(st.session_state.get("has_refreshed") and st.session_state.get("input_snapshot"))


def request_undo() -> None:
    st.session_state._pending_action = "undo"


def request_clear_filters() -> None:
    st.session_state._pending_action = "clear"


def apply_pending_action() -> None:
    """Run a queued Undo/Clear before any input widget is instantiated."""
    action = st.session_state.pop("_pending_action", None)
    if action == "undo":
        snap = st.session_state.get("input_snapshot")
        if snap:
            for key, value in snap.items():
                st.session_state[key] = value
    elif action == "clear":
        for key, value in _DEFAULT_SLIDERS.items():
            st.session_state[key] = value
