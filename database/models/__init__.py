"""ORM model aggregation.

Importing this module registers every model on ``Base.metadata`` — that is why
:func:`database.base.create_all` imports it for its side effect.
"""

from database.models.airline import Airline
from database.models.airport import Airport
from database.models.route import AirlineOffer, RouteWeek

__all__ = ["Airline", "Airport", "RouteWeek", "AirlineOffer"]
