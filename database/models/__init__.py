"""ORM model aggregation.

Importing this module registers every model on ``Base.metadata`` — that is why
:func:`database.base.create_all` imports it for its side effect.
"""

from database.models.airline import Airline
from database.models.airport import Airport
from database.models.demand import (
    DemandCalibration,
    DemandNormalized,
    RawDemandSignal,
)
from database.models.history import (
    DemandObservation,
    Route,
    SupplyObservation,
    SyncRun,
    SyncState,
    TrendObservation,
)
from database.models.route import AirlineOffer, RouteWeek

__all__ = [
    "Airline",
    "Airport",
    "RouteWeek",
    "AirlineOffer",
    # Historical / live-data models (additive; demo tables untouched).
    "Route",
    "SupplyObservation",
    "DemandObservation",
    "TrendObservation",
    "SyncRun",
    "SyncState",
    # Demand Data Platform V1.
    "RawDemandSignal",
    "DemandNormalized",
    "DemandCalibration",
]
