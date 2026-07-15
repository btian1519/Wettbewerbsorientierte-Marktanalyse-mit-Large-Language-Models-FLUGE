"""Shared vocabulary for the persistent rate-limit circuit breaker.

A single source of truth used by both the market sync (``ingestion.sync_service``)
and the demand pipeline (``backend.services.demand_service``): once a data source
signals a provider usage limit (HTTP 429 / quota / "too many requests"), it is
paused, persisted with :data:`RATE_LIMIT_STATUS`, skipped on future syncs, and the
pause survives restarts until explicitly resumed.
"""

from __future__ import annotations

# Persisted SyncState status marking a source paused after a provider usage limit.
RATE_LIMIT_STATUS = "rate_limited"

# Substrings (lower-cased) that identify a provider rate/quota limit in an error.
_RATE_LIMIT_MARKERS = ("429", "rate limit", "rate-limit", "too many requests", "quota")


def looks_rate_limited(error: str | None) -> bool:
    """True when an error message indicates a provider rate/quota limit."""
    if not error:
        return False
    e = error.lower()
    return any(marker in e for marker in _RATE_LIMIT_MARKERS)
