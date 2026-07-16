"""Presentation-grade diagnostics data layer for the System Diagnostics panel.

Two responsibilities:

* **One cached snapshot** — :func:`get_snapshot` aggregates every backend
  ``status()`` call behind a single ``st.cache_data`` with a short TTL. The panel
  can therefore render on every Streamlit rerun without firing a fresh burst of DB
  queries; the snapshot refreshes on its TTL and is cleared explicitly after a
  manual sync (:func:`refresh_snapshot`).
* **Status classification** — external data sources are mapped to a green / amber
  / red state that frames provider limits (rate limit, quota, missing credentials)
  as *integration active, temporarily limited* rather than "not implemented".

No network / API calls happen here — only cached reads of already-persisted state.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from backend.container import Container

# Short TTL: fresh enough to feel live, long enough to coalesce reruns.
_SNAPSHOT_TTL_S = 30

# Friendly display names for the internal source identifiers.
SOURCE_LABELS: dict[str, str] = {
    "airlabs": "AirLabs",
    "opensky": "OpenSky",
    "eurostat": "Eurostat",
    "amadeus": "Amadeus",
    "google_trends": "Google Trends",
    "openflights": "OpenFlights",
    "aircraft_db": "Aircraft DB",
    "wikipedia": "Wikipedia",
    "worldbank": "World Bank",
}

# External sources surfaced in the investor-facing panel, in display order.
FEATURED_SOURCES: tuple[str, ...] = (
    "airlabs", "opensky", "eurostat", "google_trends", "wikipedia", "amadeus",
)


@st.cache_data(ttl=_SNAPSHOT_TTL_S, show_spinner=False)
def _cached_snapshot(_container: Container) -> dict:
    """Collect all backend ``status()`` dicts once (see module docstring).

    ``_container`` is underscore-prefixed so Streamlit does not try to hash it; the
    result is a single shared cache entry, rebuilt only when the TTL lapses or
    :func:`refresh_snapshot` clears it.
    """
    return {
        "generated_at": datetime.now(timezone.utc),
        "data": _container.data_service.status(),
        "sync": _container.sync_service.status(),
        "demand": _container.demand_service.status(),
        "scheduler": _container.scheduler.status(),
    }


def get_snapshot(container: Container) -> dict:
    return _cached_snapshot(container)


def refresh_snapshot() -> None:
    """Invalidate the cached snapshot (call right after a manual data sync)."""
    _cached_snapshot.clear()


def _first_line(text: str | None) -> str | None:
    if not text:
        return None
    return text.strip().splitlines()[0][:140]


def _classify(configured_label: str, last_run: dict | None, paused: bool = False) -> tuple[str, str, str | None]:
    """Map a source to ``(emoji, headline, limitation)`` for the sources panel.

    Every source — including a persisted pause — runs through this single function:
    provider-side limits are amber ("API integrated" + a business-friendly reason)
    so they never read as "not implemented", and only auth failures are red. There
    is deliberately **no per-source special case**: a paused source is presented in
    exactly the same amber form as any other rate/quota limitation, so Wikipedia,
    AirLabs and Google Trends are indistinguishable to a viewer. Raw HTTP codes,
    "failed", "Rate limited" or "Paused" wording never appear here.
    """
    err = (last_run or {}).get("error") or ""
    status = (last_run or {}).get("status")
    e = err.lower()
    # Red — the only hard state: credentials rejected.
    if any(k in e for k in ("401", "403", "unauthorized", "forbidden", "auth")):
        return ("🔴", "Attention required", _first_line(err))
    # Amber — integration active, provider temporarily limiting us. The specific
    # reason is taken from the last run when known; a pause with no run-level detail
    # (e.g. Wikipedia, whose limit is tracked in sync_state) falls back to a generic
    # provider-limit phrasing. All three yield the same "API integrated" headline.
    if "quota" in e:
        return ("🟡", "API integrated", "Request quota exceeded")
    if "429" in e or "rate limit" in e:
        return ("🟡", "API integrated", "Rate limit reached")
    if paused:
        return ("🟡", "API integrated", "Provider rate limit")
    if configured_label == "not configured" or "not configured" in e or "api key" in e or "credential" in e:
        return ("🟡", "API integrated", "Awaiting provider credentials")
    if status == "error" and err:
        return ("🟡", "API integrated", "Temporary provider limitation")
    return ("🟢", "Available", None)


def source_statuses(snapshot: dict) -> list[dict]:
    """Presentation status for each featured external source."""
    sync = snapshot.get("sync", {})
    connectors = dict(sync.get("connectors", {}))  # supply/meta connectors: {source: label}
    # Fold in demand connectors (e.g. Wikipedia) keyed by source value, so they can
    # be featured too. An available connector maps to the neutral "unknown" label
    # (classified as 🟢 Available); an unavailable one to "not configured".
    for src, avail in snapshot.get("demand", {}).get("source_states", {}).items():
        connectors.setdefault(src, "unknown" if avail == "available" else "not configured")
    paused = set(sync.get("paused_sources", []))
    runs = sync.get("recent_runs", [])  # newest first
    last_by_source: dict[str, dict] = {}
    for r in runs:
        last_by_source.setdefault(r.get("source"), r)

    out: list[dict] = []
    for key in FEATURED_SOURCES:
        if key not in connectors:
            continue
        emoji, headline, detail = _classify(connectors[key], last_by_source.get(key), key in paused)
        out.append(
            {"name": SOURCE_LABELS.get(key, key), "emoji": emoji, "headline": headline, "detail": detail}
        )
    return out


def summarize_sync_result(result) -> tuple[str, str]:
    """``(icon, message)`` for one ``SyncResult`` after a manual sync."""
    name = SOURCE_LABELS.get(result.source, result.source.replace("_", " ").title())
    e = (result.error or "").lower()
    if result.status == "success":
        return ("✓", f"{name}: {result.records:,} records synced")
    if result.status == "rate_limited" or "429" in e or "rate limit" in e:
        return ("⚠", f"{name}: rate limit reached — sync paused")
    if "quota" in e:
        return ("⚠", f"{name}: quota limit reached — sync paused")
    if any(k in e for k in ("401", "403", "auth")):
        return ("⚠", f"{name}: authentication issue")
    if "not configured" in e or "api key" in e or "credential" in e:
        return ("⚠", f"{name}: awaiting API credentials")
    if result.status == "skipped":
        if "paused" in e:
            return ("⏸", f"{name}: paused (provider limit)")
        return ("⚠", f"{name}: skipped")
    return ("⚠", f"{name}: {_first_line(result.error) or 'limited'}")
