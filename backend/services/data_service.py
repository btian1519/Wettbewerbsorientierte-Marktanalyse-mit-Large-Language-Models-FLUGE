"""Data lifecycle service: schema init, seeding and status reporting.

Supply data is *persistent*: it is generated once and reused on every analysis.
``ensure_seeded`` is idempotent and cheap when the database already holds data;
``reseed`` forces a rebuild (wired to the sidebar 'Refresh' action / seed CLI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Sequence

from database.migrations import initialize_schema, reset_schema
from database.repository.interfaces import (
    AirlineRead,
    AirportRead,
    CatalogRepository,
    RouteRepository,
)
from ingestion.interfaces import MasterDataSource, SupplyDemandSource
from shared.config import Settings, get_settings
from shared.logging_config import get_logger

log = get_logger("backend.data_service")

# Given loaded master data, build the weekly supply/demand source (demo or API).
SupplySourceFactory = Callable[[Sequence[AirportRead], Sequence[AirlineRead]], SupplyDemandSource]


class DataService:
    def __init__(
        self,
        catalog_repo: CatalogRepository,
        route_repo: RouteRepository,
        master_source: MasterDataSource,
        supply_source_factory: SupplySourceFactory,
        settings: Settings | None = None,
    ) -> None:
        self._catalog_repo = catalog_repo
        self._route_repo = route_repo
        self._master = master_source
        self._supply_factory = supply_source_factory
        self._settings = settings or get_settings()
        self._last_seeded_at: datetime | None = None

    # ------------------------------------------------------------------ #
    def is_seeded(self) -> bool:
        return self._route_repo.route_count() > 0

    def ensure_seeded(self, force: bool = False) -> None:
        initialize_schema()
        if not force and self.is_seeded():
            log.info("Database already seeded (%d routes) — skipping generation", self._route_repo.route_count())
            return
        self._seed()

    def reseed(self) -> None:
        reset_schema()
        self._seed()

    def _seed(self) -> None:
        log.info("Seeding master data + demo supply/demand ...")
        # 1) master data (airports + airlines) from the mandated files
        self._catalog_repo.replace_airports(self._master.load_airports())
        self._catalog_repo.replace_airlines(self._master.load_airlines())

        # 2) weekly supply/demand facts
        airports = self._catalog_repo.list_airports()
        airlines = self._catalog_repo.list_airlines()
        source = self._supply_factory(airports, airlines)
        batch = source.produce(self._settings.demo_week)

        self._route_repo.clear_routes()
        self._route_repo.bulk_load(batch.route_rows, batch.offer_rows)
        self._last_seeded_at = datetime.now(timezone.utc)
        log.info("Seeding complete.")

    # ------------------------------------------------------------------ #
    def status(self) -> dict:
        weeks = self._route_repo.distinct_weeks()
        current = weeks[-1] if weeks else self._settings.demo_week
        return {
            "ingestion_mode": self._settings.ingestion_mode,
            "seeded": self.is_seeded(),
            "airports": self._catalog_repo.airport_count(),
            "airlines": self._catalog_repo.airline_count(),
            "routes": self._route_repo.route_count(),
            "offers": self._route_repo.offer_count(),
            "weeks": weeks,
            "current_week": current,
            "routes_by_scope": self._route_repo.route_count_by_scope(current) if weeks else {},
            "last_updated": self._last_seeded_at.isoformat() if self._last_seeded_at else "unknown (persisted)",
            "db_url": self._settings.db_url,
        }
