"""Market-scope helpers.

Route filtering by continent scope is executed in SQL (indexed ``scope`` column),
so this module only needs to *validate* scope values and encapsulate the
intercontinental invariant, keeping that domain rule in one named place.
"""

from __future__ import annotations

from database.repository.interfaces import RouteRead
from shared.constants import INTERCONTINENTAL, MARKET_SCOPES


def validate_scope(scope: str) -> None:
    if scope not in MARKET_SCOPES:
        raise ValueError(f"Unknown market scope: {scope!r}. Expected one of {MARKET_SCOPES}.")


def is_valid_for_scope(route: RouteRead, scope: str) -> bool:
    """Defensive check mirroring the storage invariant.

    Intercontinental routes must have endpoints on different continents; an
    intra-continental scope must have both endpoints on that continent.
    """
    if scope == INTERCONTINENTAL:
        return route.origin_continent != route.dest_continent
    return route.origin_continent == scope and route.dest_continent == scope
