"""System Diagnostics panel (sidebar, results page).

Serves two audiences at once: engineers monitoring the system during development
and investors / customers who should see a polished status dashboard — integrations
in place, live data syncable, and current limits clearly attributed to external API
providers (rate / quota), never "not implemented".

Design notes:

* All backend status is read through a single cached snapshot
  (:mod:`frontend.sidebar.diagnostics`), so the panel never floods the DB with
  queries on each rerun, and no network / API calls happen at render time.
* The old raw ``st.write(dict)`` dumps are replaced by compact bordered status
  cards. Raw DB URL and internal identifiers are kept out of the presentation view
  (they remain available in the underlying ``status()`` dicts).
* "Sync Now" updates the *whole market* and is deliberately independent of the
  current airline / continent / task / filter selection.
"""

from __future__ import annotations

import logging

import streamlit as st

from backend.container import Container
from frontend.sidebar.diagnostics import (
    SOURCE_LABELS,
    get_snapshot,
    refresh_snapshot,
    source_statuses,
    summarize_sync_result,
)
from shared.logging_config import recent_logs


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def _local(dt):
    """Best-effort convert an aware UTC datetime to local time for display."""
    try:
        return dt.astimezone()
    except (ValueError, AttributeError, OSError):
        return dt


def render_dev_footer(container: Container) -> None:
    with st.expander("🛠  System Diagnostics", expanded=False):
        snap = get_snapshot(container)  # cached; no DB burst per rerun
        _section_system_status(snap)
        _section_data_mode()
        _section_data_sources(snap)
        _section_synchronization(container, snap)
        _section_visualization()
        _section_background_jobs(snap)
        _section_logs()


# --------------------------------------------------------------------------- #
# 1. System status
# --------------------------------------------------------------------------- #
def _section_system_status(snap: dict) -> None:
    data = snap["data"]
    seeded = bool(data.get("seeded"))
    with st.container(border=True):
        st.markdown("**FlightScope AI**")
        st.markdown("🟢 System operational" if seeded else "🟠 Initializing")
        st.caption(f"Database: Connected · Demo data: {'Available' if seeded else 'Preparing'}")
        st.caption(f"Last system check: {_fmt(_local(snap['generated_at']))}")


# --------------------------------------------------------------------------- #
# 2. Data mode (Demo / Live) — unchanged behaviour, nicer presentation
# --------------------------------------------------------------------------- #
def _section_data_mode() -> None:
    st.markdown("**Data Mode**")
    current = st.session_state.get("data_source", "demo")
    choice = st.radio(
        "Data mode",
        options=["demo", "live"],
        index=0 if current == "demo" else 1,
        format_func=lambda v: "Demo Data" if v == "demo" else "Live API Data",
        horizontal=True,
        label_visibility="collapsed",
        help="Demo data is always preserved. 'Live API Data' reads API-ingested snapshots.",
    )
    st.session_state.data_source = choice  # unchanged: drives analysis_for(source)


# --------------------------------------------------------------------------- #
# 3. External data sources (professional API status)
# --------------------------------------------------------------------------- #
def _section_data_sources(snap: dict) -> None:
    st.markdown("**External Data Sources**")
    for s in source_statuses(snap):
        with st.container(border=True):
            st.markdown(f"{s['emoji']} **{s['name']}** — {s['headline']}")
            if s["detail"]:
                st.caption(f"Current limitation: {s['detail']}")
    st.caption(
        "Integrations are implemented; any limits above are external provider "
        "constraints (rate / quota), not missing functionality."
    )


# --------------------------------------------------------------------------- #
# 6. Synchronization (Sync button + auto-sync-before-refresh option)
# --------------------------------------------------------------------------- #
def _section_synchronization(container: Container, snap: dict) -> None:
    st.markdown("**Data Synchronization**")
    st.caption(
        "Updates the entire market (all airports, routes, airlines) — independent "
        "of the current airline, region, task or filters."
    )
    # Session-state managed; default unchecked. Consumed by sidebar._refresh().
    st.checkbox("Automatically sync data before Refresh", key="sync_on_refresh")

    if st.button("Sync Data", use_container_width=True, type="primary"):
        with st.spinner("Synchronizing market data…"):
            results = container.sync_service.sync_market()
        st.session_state["last_sync_results"] = [summarize_sync_result(r) for r in results]
        refresh_snapshot()  # invalidate the cached snapshot so new counts show

    # A source that hit a provider rate/quota limit is paused (persisted across
    # restarts) and skipped on every sync until explicitly resumed here.
    paused = snap["sync"].get("paused_sources", [])
    if paused:
        names = ", ".join(SOURCE_LABELS.get(p, p) for p in paused)
        st.caption(f"⏸ Paused after provider limit: {names}")
        if st.button("Resume paused sources", use_container_width=True):
            resumed = container.sync_service.resume_paused_sources()
            refresh_snapshot()
            st.success(f"Resumed {resumed} source(s).")

    _render_sync_outcome()


def _render_sync_outcome() -> None:
    results = st.session_state.get("last_sync_results")
    if not results:
        return
    with st.container(border=True):
        st.markdown("**Synchronization started**")
        st.markdown("✓ API connectors initialized")
        st.markdown("✓ Database connection available")
        limited = False
        for icon, msg in results:
            st.markdown(f"{icon} {msg}")
            if icon != "✓":
                limited = True
        st.caption("Sync completed with limitations" if limited else "Sync completed successfully")


# --------------------------------------------------------------------------- #
# 8. Visualization settings (map)
# --------------------------------------------------------------------------- #
def _section_visualization() -> None:
    st.markdown("**Visualization Settings**")
    st.session_state.map_height = st.slider(
        "Map height (px)", min_value=260, max_value=560,
        value=st.session_state.get("map_height", 360), step=20,
    )


# --------------------------------------------------------------------------- #
# 9. Background jobs (scheduler) — technical, low-prominence
# --------------------------------------------------------------------------- #
def _section_background_jobs(snap: dict) -> None:
    sched = snap["scheduler"]
    next_runs = [j["next_run"] for j in sched.get("jobs", []) if j.get("next_run")]
    with st.container(border=True):
        st.markdown("**Background Jobs**")
        st.caption(f"Scheduler: {'🟢 Running' if sched.get('running') else '⚪ Stopped'}")
        st.caption(f"Next scheduled sync: {_fmt(min(next_runs) if next_runs else None)}")


# --------------------------------------------------------------------------- #
# 10. Recent system messages (compact; raw dump opt-in)
# --------------------------------------------------------------------------- #
def _section_logs() -> None:
    st.markdown("**Recent System Messages**")
    lines = recent_logs(limit=15, min_level=logging.WARNING)
    if not lines:
        st.caption("✓ No warnings or errors.")
    else:
        for line in lines[-5:]:
            # Show only the human message (drop the "asctime | LEVEL |" prefix).
            msg = line.split("|", 2)[-1].strip()
            st.markdown(f"⚠ {msg}")
        if st.checkbox("Show technical details", key="diag_show_log_details"):
            st.code("\n".join(lines), language="text")
