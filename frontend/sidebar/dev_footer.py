"""Collapsible developer / diagnostics footer.

Cleanly separates two independent concerns per the target architecture:

* **Analysis Status** — what the user is currently analysing (scope / airline /
  task). Driven purely by UI selection; touches no APIs.
* **Data Status** — the global market database: record counts, last sync,
  coverage and per-source state. Driven only by the sync layer.

"Sync Now" updates the *whole market* and is deliberately independent of the
current airline/continent/task/filter selection.
"""

from __future__ import annotations

import logging

import streamlit as st

from backend.container import Container
from shared.logging_config import recent_logs
from shared.sources import DataSource, SyncCategory


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def render_dev_footer(container: Container) -> None:
    with st.expander("🛠  Developer / Diagnostics", expanded=False):
        data_status = container.data_service.status()

        st.markdown("**Tool status**")
        st.write("🟢 Running" if data_status["seeded"] else "🟠 Not seeded")

        # --- Data source switch (demo default; live is a parallel read) ---
        current = st.session_state.get("data_source", "demo")
        choice = st.radio(
            "Analysis reads from",
            options=["demo", "live"],
            index=0 if current == "demo" else 1,
            horizontal=True,
            help="Demo data is always preserved. 'Live' reads API-ingested snapshots.",
        )
        st.session_state.data_source = choice

        _render_analysis_status(container)
        _render_data_status(container, data_status)
        _render_demand_status(container)
        _render_sync_controls(container)
        _render_scheduler(container)

        # --- Map rendering options ---------------------------------------
        st.markdown("**Map rendering options**")
        st.session_state.map_height = st.slider(
            "Map height (px)", min_value=260, max_value=560,
            value=st.session_state.get("map_height", 360), step=20,
        )

        # --- Logs --------------------------------------------------------
        st.markdown("**Error logs** (warnings and above)")
        logs = recent_logs(limit=15, min_level=logging.WARNING)
        st.code("\n".join(logs) if logs else "No warnings or errors.", language="text")

        st.caption(f"DB: {data_status['db_url']}")


# --------------------------------------------------------------------------- #
def _render_analysis_status(container: Container) -> None:
    st.markdown("### 🔎 Analysis Status")
    response = st.session_state.get("response")
    if response is not None:
        airline = container.catalog_service.airline(response.airline_iata)
        st.write(
            {
                "source": st.session_state.get("data_source", "demo"),
                "continent": response.scope,
                "airline": airline.name if airline else response.airline_iata,
                "task": response.task.value,
                "week": response.week,
                **response.stats,
            }
        )
    else:
        st.caption("No analysis run yet — configure the scope and press Analyze/Refresh.")


def _render_data_status(container: Container, data_status: dict) -> None:
    sync = container.sync_service.status()
    counts = sync["counts"]
    supply_cov = next(
        (
            c for c in sync["coverage"]
            if c["data_source"] == DataSource.AIRLABS.value
            and c["category"] == SyncCategory.SCHEDULES.value
        ),
        None,
    )

    st.markdown("### 🗄️ Data Status")
    st.write(
        {
            "supply_database": f"{counts['supply_observations']:,} route-airline records",
            "last_supply_sync": _fmt(sync["last_supply_refresh"]),
            "coverage": (supply_cov or {}).get("coverage_scope") or "—",
            "demand_database": f"{counts['demand_observations']:,} route-week records",
            "last_demand_sync": _fmt(sync["last_demand_refresh"]),
            "routes_known": counts["routes"],
            "snapshots": counts["supply_snapshots"] + counts["demand_snapshots"],
        }
    )
    st.caption("Demo database (untouched): "
               f"{data_status['routes']:,} routes · {data_status['offers']:,} offers")

    st.markdown("**API status**")
    st.write(sync["connectors"])

    if sync["coverage"]:
        st.caption("Coverage by source")
        st.write(
            [
                {"source": c["data_source"], "category": c["category"],
                 "scope": c["coverage_scope"], "status": c["sync_status"],
                 "records": c["records"], "at": _fmt(c["sync_timestamp"])}
                for c in sync["coverage"]
            ]
        )


def _render_demand_status(container: Container) -> None:
    d = container.demand_service.status()
    st.markdown("### 📈 Demand Status")
    st.write(
        {
            "last_demand_sync": _fmt(d["last_demand_sync"]),
            "od_pairs": d["od_pairs"],
            "signals": d["signals"],
            "normalized_rows": d["normalized_rows"],
            "last_calculation_version": d["last_calculation_version"] or "—",
            "avg_confidence": d["avg_confidence"] if d["avg_confidence"] is not None else "—",
        }
    )
    st.caption("Demand sources")
    st.write(d["sources"])


def _render_sync_controls(container: Container) -> None:
    st.markdown("### 🔄 Data Sync")
    st.caption(
        "Updates the entire market (all airports / routes / airlines). Independent "
        "of the selected airline, continent, task or filters."
    )
    if st.button("SYNC NOW!", use_container_width=True, type="primary"):
        with st.spinner("Syncing global market data…"):
            results = container.sync_service.sync_market()
        for r in results:
            if r.status == "success":
                st.success(f"{r.source} · {r.category}: {r.records} records ({r.coverage_scope}).")
            else:
                st.warning(f"{r.source} · {r.category}: {r.status} — {r.error}")


def _render_scheduler(container: Container) -> None:
    sched = container.scheduler.status()
    st.markdown(f"### ⏱️ Scheduler — {'🟢 running' if sched['running'] else '⚪ stopped'}")
    st.caption("Background jobs run exactly like 'Sync Now' (global, UI-independent).")
    for job in sched["jobs"]:
        st.caption(
            f"{job['id']}: every {job['interval_s']}s · last {_fmt(job['last_run'])} · "
            f"next {_fmt(job['next_run'])}"
        )
