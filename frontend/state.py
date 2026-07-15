"""Session-state helpers.

Encapsulates all ``st.session_state`` keys behind named functions so pages never
touch raw string keys and the state schema is documented in one place.

Inputs are **keyed** widgets (``airline``/``scope``/``task`` and the slider keys
``sl_margin``/``sl_net``). Because a keyed widget's value cannot be mutated after
the widget is instantiated in the same run, Undo/Clear register a *pending
action* and :func:`apply_pending_action` applies it at the very top of the next
run — before any widget is created.

Undo keeps exactly two full-analysis snapshots — ``current_snapshot`` and
``previous_snapshot`` — so a single Undo restores the whole previously computed
analysis (inputs *and* results/map/show-more) without any recomputation. There is
deliberately one Undo level: no stack, no history, no redo.

Streamlit quirk (important): an externally pre-set ``session_state`` value is
ignored on a widget's **first** instantiation — only ``value=`` is honoured then.
So the sliders are *not* seeded in ``init_state``; :func:`filter_slider` passes
``value=`` on the first render and lets ``session_state`` drive it afterwards
(which is also what lets Undo/Clear set the value on later renders).

Network Availability default vs. user value: the slider's default depends on the
analysis direction (100 % for market gaps, 0 % for overcapacities). To tell an
auto-applied default from a value the user deliberately chose, ``net_customized``
records whether the user moved the slider *this session*. While it is False the
default is re-asserted on every rerun (so a Task change updates it); once True the
user's value is preserved across Task changes and Refresh. The flag is part of the
Undo snapshot and is reset by Clear All Filters. See
:func:`sync_network_availability`.
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
from shared.logging_config import get_logger

log = get_logger("frontend.state")

# Slider keys hold integer percentages; converted to 0..1 for the model.
_DEFAULT_SLIDERS = {
    "sl_margin": int(round(DEFAULT_MARGE_AVERAGE * 100)),
    "sl_net": int(round(DEFAULT_NETWORK_AVAILABILITY * 100)),
}
# Editable scope inputs (keyed widgets, restored programmatically on Undo/Clear).
_INPUT_KEYS = ("airline", "scope", "task", *_DEFAULT_SLIDERS.keys())
# Analysis-state keys: together with the inputs they fully describe one computed
# analysis. Results, ranking, map view and the show-more count all derive from
# these, so restoring them reproduces the exact view without recomputation.
_ANALYSIS_KEYS = ("response", "visible", "map_height")
# Extra UI-state kept in the snapshot: whether the user customized the Network
# Availability slider (so Undo restores value *and* the default-vs-custom status).
_META_KEYS = ("net_customized",)
# A full snapshot = inputs + analysis state + tracked UI meta (one restorable view).
_SNAPSHOT_KEYS = (*_INPUT_KEYS, *_ANALYSIS_KEYS, *_META_KEYS)
# Fallback values used when a key is absent while capturing a snapshot.
_SNAPSHOT_DEFAULTS = {
    "airline": None, "scope": None, "task": None,
    **_DEFAULT_SLIDERS,
    "response": None, "visible": TOP_VISIBLE_RESULTS, "map_height": 360,
    "net_customized": False,
}


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("page", "start")
    ss.setdefault("visible", TOP_VISIBLE_RESULTS)
    ss.setdefault("response", None)
    # Undo support: exactly two full-analysis snapshots — one Undo level, no redo.
    ss.setdefault("current_snapshot", None)
    ss.setdefault("previous_snapshot", None)
    ss.setdefault("_pending_action", None)
    # Whether the user moved the Network Availability slider this session. False on
    # every fresh Streamlit session, so the direction-dependent default applies.
    ss.setdefault("net_customized", False)
    # NB: slider keys (sl_margin/sl_net) are intentionally NOT seeded here —
    # see the module docstring; filter_slider() supplies the first-render default.


def go_to(page: str) -> None:
    st.session_state.page = page


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #
def _net_default_for_task(task_value: str | None) -> int:
    """Network Availability slider default (0–100 %) for a given analysis direction.

    A market gap (Find new opportunities, Z > 0) defaults to 100 %, an overcapacity
    (Identify overcapacities, Z < 0) to 0 %. With the direction-dependent factor F
    both resolve to the same neutral baseline F = 1.0. Pure — no session access.
    """
    if task_value == Task.OVERCAPACITIES.value:
        return 0
    return int(round(DEFAULT_NETWORK_AVAILABILITY * 100))


def _slider_default(key: str) -> int:
    """Default position (0–100 %) for a filter slider (Network Availability is
    direction-dependent; see :func:`_net_default_for_task`)."""
    if key == "sl_net":
        return _net_default_for_task(st.session_state.get("task"))
    return _DEFAULT_SLIDERS[key]


def mark_net_customized() -> None:
    """Network Availability slider ``on_change`` callback.

    Fires only on *user* interaction (never on programmatic updates), so it flags
    that the current value is a deliberate user choice to be preserved.
    """
    st.session_state["net_customized"] = True


def sync_network_availability() -> None:
    """Re-assert the mode default for Network Availability unless the user chose it.

    Central rule, run once per rerun *before* the sidebar renders (see ``app.py``):

    * ``net_customized`` is False → set the slider to the current Task/delta default
      (this is what makes a Task change update the value).
    * ``net_customized`` is True  → keep the user's value untouched.

    No-op until the slider has been instantiated at least once (its first-render
    default is supplied by :func:`filter_slider`); this avoids Streamlit's
    first-instantiation quirk of ignoring a pre-set value.
    """
    ss = st.session_state
    if "sl_net" not in ss:
        return
    if ss.get("net_customized", False):
        log.debug("Network Availability: user customized value retained (%s%%)", ss["sl_net"])
        return
    default = _net_default_for_task(ss.get("task"))
    if ss["sl_net"] != default:
        log.debug("Network Availability: default value applied (%s%%)", default)
    ss["sl_net"] = default


def filter_slider(label: str, key: str, on_change=None) -> None:
    """Render a 0–100% filter slider that shows its default on first render.

    ``value=`` is supplied only until the key exists in ``session_state``;
    thereafter the widget (and Undo/Clear, which set ``session_state[key]`` before
    the widget) drive it. This works around Streamlit ignoring an externally
    pre-set value on a widget's first instantiation. ``on_change`` lets the caller
    hook user edits (e.g. Network Availability customization tracking).
    """
    kwargs = {} if key in st.session_state else {"value": _slider_default(key)}
    st.slider(label, 0, 100, key=key, format="%d%%", on_change=on_change, **kwargs)


def current_filter_settings() -> FilterSettings:
    ss = st.session_state
    return FilterSettings(
        marge_average=ss.get("sl_margin", _slider_default("sl_margin")) / 100.0,
        network_availability=ss.get("sl_net", _slider_default("sl_net")) / 100.0,
        # Distance Efficiency has no UI slider; use the fixed default so the engine
        # keeps working and the filter can be re-enabled later.
        min_distance_efficiency=DEFAULT_MIN_DISTANCE_EFFICIENCY,
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
def _capture_snapshot() -> dict:
    """Copy the complete current analysis state (inputs + results + meta) into a dict.

    Slider keys fall back to their (task-aware) default when never rendered yet, so
    an initial analysis started from the start page still snapshots a sensible value.
    """
    ss = st.session_state
    snap: dict = {}
    for k in _SNAPSHOT_KEYS:
        default = _slider_default(k) if k in _DEFAULT_SLIDERS else _SNAPSHOT_DEFAULTS[k]
        snap[k] = ss.get(k, default)
    return snap


def commit_analysis_snapshot(*, is_refresh: bool) -> None:
    """Record the just-computed analysis as the *current* snapshot.

    Initial Analyze (``is_refresh=False``): ``current = A`` and ``previous = None``
    — Undo stays disabled. Refresh (``is_refresh=True``): the analysis being
    replaced is preserved as ``previous`` before ``current`` is overwritten, which
    is what gives Undo exactly one level::

        previous = current   # the analysis about to be replaced
        current  = <new analysis just computed>
    """
    ss = st.session_state
    if is_refresh:
        ss.previous_snapshot = ss.current_snapshot
    ss.current_snapshot = _capture_snapshot()


def can_undo() -> bool:
    # Enabled once a previous analysis exists (i.e. after the first Refresh) and
    # stays enabled after an Undo — previous is left intact, so there is no redo.
    return st.session_state.get("previous_snapshot") is not None


def request_undo() -> None:
    st.session_state._pending_action = "undo"


def request_clear_filters() -> None:
    st.session_state._pending_action = "clear"


def apply_pending_action() -> None:
    """Run a queued Undo/Clear before any input widget is instantiated."""
    action = st.session_state.pop("_pending_action", None)
    if action == "undo":
        snap = st.session_state.get("previous_snapshot")
        if snap:
            # Restore the full previous analysis — inputs, results, map view and
            # show-more count. Pure state replay: no recomputation, no API/DB call.
            for key, value in snap.items():
                st.session_state[key] = value
            # The restored analysis becomes current; previous is left unchanged so
            # a repeated Undo is idempotent (single level, no redo).
            st.session_state.current_snapshot = snap
    elif action == "clear":
        for key in _DEFAULT_SLIDERS:
            st.session_state[key] = _slider_default(key)
        # Network Availability reverts to its mode default and to auto-default mode.
        st.session_state["net_customized"] = False
