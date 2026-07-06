"""Repository package: persistence-facing contracts and their SQLAlchemy impl."""

from database.repository.interfaces import (
    AirlineRead,
    AirportRead,
    CatalogRepository,
    OfferRead,
    RouteRead,
    RouteRepository,
)
from database.repository.sqlalchemy_repo import (
    SqlAlchemyCatalogRepository,
    SqlAlchemyRouteRepository,
)

__all__ = [
    "AirportRead",
    "AirlineRead",
    "OfferRead",
    "RouteRead",
    "CatalogRepository",
    "RouteRepository",
    "SqlAlchemyCatalogRepository",
    "SqlAlchemyRouteRepository",
]
