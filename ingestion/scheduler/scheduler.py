"""APScheduler wrapper for background sync jobs.

Runs in-process with a ``BackgroundScheduler`` (Celery-compatible structure: jobs
are plain callables, so moving them to Celery tasks later is mechanical). It never
auto-starts unless ``settings.scheduler_autostart`` is set — a live scheduler
inside a Streamlit process is opt-in. ``status()`` feeds the dev footer with the
last/next run per job.
"""

from __future__ import annotations

from datetime import datetime

from ingestion.scheduler.jobs import JobSpec, build_jobs
from ingestion.sync_service import SyncService
from shared.config import Settings, get_settings
from shared.logging_config import get_logger

log = get_logger("ingestion.scheduler")


class SyncScheduler:
    def __init__(self, sync_service: SyncService, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._jobs: list[JobSpec] = build_jobs(sync_service, self._settings)
        self._scheduler = None  # lazily created (APScheduler optional at runtime)
        self._last_run: dict[str, datetime] = {}

    # ------------------------------------------------------------------ #
    def start(self) -> bool:
        """Start the background scheduler (idempotent). Returns True if running."""
        if self._scheduler is not None:
            return True
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
        except Exception as exc:  # pragma: no cover
            log.warning("APScheduler unavailable, scheduler disabled: %s", exc)
            return False

        scheduler = BackgroundScheduler(daemon=True)
        for job in self._jobs:
            scheduler.add_job(
                self._wrap(job),
                trigger=IntervalTrigger(seconds=job.interval_seconds),
                id=job.id,
                name=job.id,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        scheduler.start()
        self._scheduler = scheduler
        log.info("Scheduler started with %d jobs", len(self._jobs))
        return True

    def _wrap(self, job: JobSpec):
        def _run() -> None:
            self._last_run[job.id] = datetime.now()
            try:
                job.run()
            except Exception as exc:  # noqa: BLE001 - never kill the scheduler
                log.error("Scheduled job %s failed: %s", job.id, exc)

        return _run

    def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    # ------------------------------------------------------------------ #
    def status(self) -> dict:
        running = self._scheduler is not None and getattr(self._scheduler, "running", False)
        jobs = []
        for job in self._jobs:
            next_run = None
            if self._scheduler is not None:
                sj = self._scheduler.get_job(job.id)
                next_run = getattr(sj, "next_run_time", None) if sj else None
            jobs.append(
                {
                    "id": job.id,
                    "interval_s": job.interval_seconds,
                    "last_run": self._last_run.get(job.id),
                    "next_run": next_run,
                }
            )
        return {"running": running, "jobs": jobs}
