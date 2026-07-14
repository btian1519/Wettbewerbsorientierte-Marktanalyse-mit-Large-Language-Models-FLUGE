"""Composition root / dependency-injection container.

All concrete implementations are chosen here and injected into services. The demo
path (``analysis_service`` over the demo route repository) is unchanged. The live
path is built *in parallel*: connectors → sync service → observation repository →
``live_analysis_service`` over a live route repository. ``analysis_for(source)``
lets the UI pick which one to read from (default: demo).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.services.analysis_service import AnalysisService
from backend.services.catalog_service import CatalogService
from backend.services.data_service import DataService
from backend.services.demand_service import DemandService
from database.repository.demand_repo import SqlAlchemyDemandRepository
from database.repository.interfaces import AirlineRead, AirportRead
from database.repository.observation_repo import (
    SqlAlchemyLiveRouteRepository,
    SqlAlchemyObservationRepository,
)
from ingestion.demand.eurostat_connector import EurostatDemandConnector
from ingestion.demand.google_trends_connector import GoogleTrendsDemandConnector
from ingestion.demand.wikipedia_connector import WikipediaDemandConnector
from ingestion.demand.worldbank_connector import WorldBankConnector
from database.repository.sqlalchemy_repo import (
    SqlAlchemyCatalogRepository,
    SqlAlchemyRouteRepository,
)
from ingestion.connectors import (
    AircraftDbConnector,
    AirLabsConnector,
    AmadeusConnector,
    EurostatConnector,
    GoogleTrendsConnector,
    OpenFlightsConnector,
    OpenSkyConnector,
)
from ingestion.connectors.base import BaseConnector
from ingestion.demo_generator import DemoDataSource
from ingestion.interfaces import SupplyDemandSource
from ingestion.master_data import FileMasterDataSource
from ingestion.scheduler import SyncScheduler
from ingestion.sync_service import SyncService
from shared.config import Settings, get_settings
from shared.logging_config import configure_logging, get_logger
from shared.sources import DataSource

log = get_logger("backend.container")


@dataclass
class Container:
    settings: Settings
    catalog_service: CatalogService
    data_service: DataService
    analysis_service: AnalysisService            # demo (default)
    live_analysis_service: AnalysisService       # live observations
    sync_service: SyncService
    demand_service: DemandService
    scheduler: SyncScheduler

    def analysis_for(self, data_source: str) -> AnalysisService:
        """Pick the analysis service for the selected data source ('demo'|'live')."""
        return self.live_analysis_service if data_source == "live" else self.analysis_service


def _make_supply_factory(settings: Settings):
    def factory(airports: Sequence[AirportRead], airlines: Sequence[AirlineRead]) -> SupplyDemandSource:
        # Demo data is generated here regardless of ingestion_mode; live data is a
        # parallel path (see sync_service) that never overwrites the demo tables.
        return DemoDataSource(airports, airlines, settings)

    return factory


def _build_connectors(settings: Settings) -> tuple[dict[DataSource, BaseConnector], AircraftDbConnector]:
    aircraft = AircraftDbConnector(settings)
    connectors: dict[DataSource, BaseConnector] = {
        DataSource.AIRLABS: AirLabsConnector(settings),
        DataSource.OPENSKY: OpenSkyConnector(settings),
        DataSource.EUROSTAT: EurostatConnector(settings),
        DataSource.AMADEUS: AmadeusConnector(settings),
        DataSource.GOOGLE_TRENDS: GoogleTrendsConnector(settings),
        DataSource.OPENFLIGHTS: OpenFlightsConnector(settings),
        DataSource.AIRCRAFT_DB: aircraft,
    }
    return connectors, aircraft


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    # --- Demo path (unchanged) -----------------------------------------
    catalog_repo = SqlAlchemyCatalogRepository()
    route_repo = SqlAlchemyRouteRepository()
    master_source = FileMasterDataSource(settings)
    data_service = DataService(
        catalog_repo=catalog_repo,
        route_repo=route_repo,
        master_source=master_source,
        supply_source_factory=_make_supply_factory(settings),
        settings=settings,
    )
    catalog_service = CatalogService(catalog_repo)
    analysis_service = AnalysisService(route_repo, catalog_service)

    # --- Live path (parallel, additive) --------------------------------
    obs_repo = SqlAlchemyObservationRepository()

    # Demand Data Platform (rule-based V1; ML-ready via the injected model).
    demand_repo = SqlAlchemyDemandRepository()
    demand_connectors = [
        GoogleTrendsDemandConnector(settings),
        WikipediaDemandConnector(settings),
        EurostatDemandConnector(settings),
        WorldBankConnector(settings),
    ]
    demand_service = DemandService(demand_repo, obs_repo, catalog_service, demand_connectors, settings=settings)

    # Live analysis reads demand ONLY through demand_service.get_weekly_demand.
    live_route_repo = SqlAlchemyLiveRouteRepository(demand_provider=demand_service)
    live_analysis_service = AnalysisService(live_route_repo, catalog_service)

    connectors, aircraft = _build_connectors(settings)
    sync_service = SyncService(
        obs_repo, catalog_service, connectors, aircraft, settings, demand_service=demand_service
    )
    scheduler = SyncScheduler(sync_service, settings)
    if settings.scheduler_autostart:
        scheduler.start()

    return Container(
        settings=settings,
        catalog_service=catalog_service,
        data_service=data_service,
        analysis_service=analysis_service,
        live_analysis_service=live_analysis_service,
        sync_service=sync_service,
        demand_service=demand_service,
        scheduler=scheduler,
    )
