"""Job definitions: which sync category runs, how often.

Frequencies come from :class:`~shared.config.Settings` (env-overridable), matching
the brief: airport metadata monthly, schedules daily, prices daily, demand weekly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ingestion.sync_service import SyncResult, SyncService
from shared.config import Settings
from shared.sources import SyncCategory


@dataclass(frozen=True)
class JobSpec:
    id: str
    category: SyncCategory
    interval_seconds: int
    run: Callable[[], SyncResult | None]


def build_jobs(sync_service: SyncService, settings: Settings) -> list[JobSpec]:
    """Background jobs. Each runs exactly like "Sync Now" for its category — a
    global market update, with no knowledge of any UI selection."""
    return [
        JobSpec(
            "supply", SyncCategory.SCHEDULES, settings.sync_interval_schedules,
            lambda: sync_service.run_category(SyncCategory.SCHEDULES),
        ),
        JobSpec(
            "demand", SyncCategory.DEMAND, settings.sync_interval_demand,
            lambda: sync_service.run_category(SyncCategory.DEMAND),
        ),
        JobSpec(
            "metadata", SyncCategory.AIRPORT_METADATA, settings.sync_interval_airport_metadata,
            lambda: sync_service.run_category(SyncCategory.AIRPORT_METADATA),
        ),
    ]
