"""Composition root / dependency-injection container.

All concrete implementations are chosen here and injected into services. Nothing
else in the codebase constructs a repository or a data source directly, so
swapping SQLite→PostgreSQL or demo→API is a change confined to this one file
(driven by :mod:`shared.config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.services.analysis_service import AnalysisService
from backend.services.catalog_service import CatalogService
from backend.services.data_service import DataService
from database.repository.sqlalchemy_repo import (
    SqlAlchemyCatalogRepository,
    SqlAlchemyRouteRepository,
)
from database.repository.interfaces import AirlineRead, AirportRead
from ingestion.demo_generator import DemoDataSource
from ingestion.interfaces import SupplyDemandSource
from ingestion.master_data import FileMasterDataSource
from shared.config import Settings, get_settings
from shared.logging_config import configure_logging, get_logger

log = get_logger("backend.container")


@dataclass
class Container:
    settings: Settings
    catalog_service: CatalogService
    data_service: DataService
    analysis_service: AnalysisService


def _make_supply_factory(settings: Settings):
    def factory(airports: Sequence[AirportRead], airlines: Sequence[AirlineRead]) -> SupplyDemandSource:
        if settings.ingestion_mode == "api":
            # Prepared path: a live provider would be constructed here.
            from ingestion.api_interfaces import FlightOffersApi

            log.warning("ingestion_mode='api' selected but live APIs are not implemented; "
                        "falling back to demo generator.")
            _ = FlightOffersApi  # referenced to document the seam
        return DemoDataSource(airports, airlines, settings)

    return factory


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

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

    return Container(
        settings=settings,
        catalog_service=catalog_service,
        data_service=data_service,
        analysis_service=analysis_service,
    )
