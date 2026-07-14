"""API connectors — one resilient client per external data source.

Each connector inherits auth, retry, rate limiting, error handling, logging and
validation from :class:`~ingestion.connectors.base.BaseConnector`. AirLabs is
fully implemented; the others are prepared with the same structure so enabling a
source is a focused change, never a framework change.
"""

from ingestion.connectors.aircraft_db_connector import AircraftDbConnector
from ingestion.connectors.airlabs_connector import AirLabsConnector
from ingestion.connectors.amadeus_connector import AmadeusConnector
from ingestion.connectors.base import (
    BaseConnector,
    ConnectorError,
    ConnectorStatus,
)
from ingestion.connectors.eurostat_connector import EurostatConnector
from ingestion.connectors.google_trends_connector import GoogleTrendsConnector
from ingestion.connectors.openflights_connector import OpenFlightsConnector
from ingestion.connectors.opensky_connector import OpenSkyConnector

__all__ = [
    "BaseConnector",
    "ConnectorError",
    "ConnectorStatus",
    "AirLabsConnector",
    "OpenSkyConnector",
    "EurostatConnector",
    "AmadeusConnector",
    "GoogleTrendsConnector",
    "OpenFlightsConnector",
    "AircraftDbConnector",
]
