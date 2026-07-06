"""Domain constants shared across the whole application.

Only *structural* domain vocabulary lives here (continents, task modes, default
model parameters). Business **data** — airlines and airports — is deliberately
NOT defined here; it is loaded exclusively from the external ``AIRLINES.py`` and
``AIRPORTS.xlsx`` files by the catalog layer, per project constraint.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

# --------------------------------------------------------------------------- #
# Continents
# --------------------------------------------------------------------------- #
# Physical continents a single airport can belong to.
AIRPORT_CONTINENTS: Final[tuple[str, ...]] = (
    "Africa",
    "North America",
    "South America",
    "Europe",
    "Asia",
    "Oceania",
)

# Special market scope: only routes whose endpoints lie on *different* continents.
INTERCONTINENTAL: Final[str] = "Global/Intercontinental"

# The full set of scope options offered in the UI (order = display order).
MARKET_SCOPES: Final[tuple[str, ...]] = AIRPORT_CONTINENTS + (INTERCONTINENTAL,)


class Task(str, Enum):
    """Analysis modes."""

    OPPORTUNITIES = "Find new opportunities"
    OVERCAPACITIES = "Identify overcapacities"


TASKS: Final[tuple[str, ...]] = tuple(t.value for t in Task)


# --------------------------------------------------------------------------- #
# Analysis model defaults (see backend.analysis.engine for the formula)
# --------------------------------------------------------------------------- #
DEFAULT_MARGE_AVERAGE: Final[float] = 0.20
DEFAULT_NETWORK_AVAILABILITY: Final[float] = 1.0
DEFAULT_MIN_DISTANCE_EFFICIENCY: Final[float] = 0.0

# Reference distance (km) at which distance efficiency peaks at 1.0.
DISTANCE_EFFICIENCY_PEAK_KM: Final[float] = 2000.0
DISTANCE_EFFICIENCY_SPREAD_KM: Final[float] = 10000.0

# How many results the ranking returns and how they are paged in the UI.
TOP_N_RESULTS: Final[int] = 10
TOP_VISIBLE_RESULTS: Final[int] = 3
SHOW_MORE_RESULTS: Final[int] = 7  # 3 + 7 = 10
