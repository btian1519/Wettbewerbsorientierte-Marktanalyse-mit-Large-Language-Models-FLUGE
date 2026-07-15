"""Network Availability slider state logic (default vs. user-customized).

These exercise frontend.state without a running Streamlit app by swapping the
module-level ``st`` for a fake whose ``session_state`` is a dict supporting both
item and attribute access (as Streamlit's SessionStateProxy does).
"""

from __future__ import annotations

import pytest

import frontend.state as state
from shared.constants import Task


class _FakeSessionState(dict):
    """Dict that also allows attribute access, like st.session_state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover - mirrors AttributeError contract
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _FakeSt:
    def __init__(self) -> None:
        self.session_state = _FakeSessionState()

    def slider(self, *args, **kwargs):  # pragma: no cover - not used here
        return None


@pytest.fixture
def ss(monkeypatch):
    fake = _FakeSt()
    monkeypatch.setattr(state, "st", fake)
    state.init_state()
    return fake.session_state


def _render_net_first_time(ss, value: int) -> None:
    """Simulate the slider's first render seeding session_state (no customization)."""
    ss["sl_net"] = value


# --------------------------------------------------------------------------- #
# Pure default logic
# --------------------------------------------------------------------------- #
def test_net_default_by_direction():
    assert state._net_default_for_task(Task.OPPORTUNITIES.value) == 100
    assert state._net_default_for_task(Task.OVERCAPACITIES.value) == 0
    assert state._net_default_for_task(None) == 100  # not chosen yet -> gap default


# Test 1: new session, opportunities -> default 100
def test_default_opportunities(ss):
    ss["task"] = Task.OPPORTUNITIES.value
    _render_net_first_time(ss, 100)
    state.sync_network_availability()
    assert ss["sl_net"] == 100
    assert ss["net_customized"] is False


# Test 2: switch to overcapacities without a slider change -> 0, still not customized
def test_switch_to_overcapacities_resets_default(ss):
    ss["task"] = Task.OPPORTUNITIES.value
    _render_net_first_time(ss, 100)
    state.sync_network_availability()
    ss["task"] = Task.OVERCAPACITIES.value  # user changes mode
    state.sync_network_availability()
    assert ss["sl_net"] == 0
    assert ss["net_customized"] is False


# Test 3: user moves the slider -> customized True
def test_user_edit_marks_customized(ss):
    state.mark_net_customized()
    assert ss["net_customized"] is True


# Test 4: customized value is retained across a Task change
def test_customized_value_retained_on_task_change(ss):
    ss["task"] = Task.OPPORTUNITIES.value
    _render_net_first_time(ss, 100)
    ss["sl_net"] = 60
    state.mark_net_customized()
    ss["task"] = Task.OVERCAPACITIES.value
    state.sync_network_availability()
    assert ss["sl_net"] == 60
    assert ss["net_customized"] is True


# Test 5: Clear All Filters -> current default + customized reset
def test_clear_resets_to_default_and_flag(ss):
    ss["task"] = Task.OVERCAPACITIES.value
    _render_net_first_time(ss, 60)
    ss["net_customized"] = True
    state.request_clear_filters()
    state.apply_pending_action()
    assert ss["sl_net"] == 0  # overcapacities default
    assert ss["net_customized"] is False


# Test 6: Undo restores both the slider value and the customized flag
def test_undo_restores_value_and_customized(ss):
    ss["task"] = Task.OPPORTUNITIES.value
    _render_net_first_time(ss, 100)
    ss["net_customized"] = False
    state.commit_analysis_snapshot(is_refresh=False)  # snapshot A: 100 / False

    # User customizes to 40 % and refreshes -> snapshot B, previous = A
    ss["sl_net"] = 40
    ss["net_customized"] = True
    state.commit_analysis_snapshot(is_refresh=True)

    state.request_undo()
    state.apply_pending_action()
    assert ss["sl_net"] == 100
    assert ss["net_customized"] is False


def test_refresh_keeps_customized_value(ss):
    """Refresh with an existing user value must not revert it."""
    ss["task"] = Task.OPPORTUNITIES.value
    _render_net_first_time(ss, 100)
    ss["sl_net"] = 75
    state.mark_net_customized()
    state.sync_network_availability()  # runs on the post-refresh rerun
    assert ss["sl_net"] == 75
    assert ss["net_customized"] is True
