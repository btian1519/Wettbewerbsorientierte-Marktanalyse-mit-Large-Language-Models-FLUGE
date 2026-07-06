"""Ranking of scored routes.

* Opportunities → **maximise** benefit (largest untapped market gaps first).
* Overcapacities → **minimise** benefit (most negative = worst oversupply first).
"""

from __future__ import annotations

from typing import Sequence

from backend.analysis.engine import ScoredRoute
from shared.constants import TOP_N_RESULTS, Task


def rank_scored(
    scored: Sequence[ScoredRoute], task: Task, top_n: int = TOP_N_RESULTS
) -> list[ScoredRoute]:
    reverse = task == Task.OPPORTUNITIES  # maximise for opportunities
    ordered = sorted(scored, key=lambda s: s.benefit_eur, reverse=reverse)
    return ordered[:top_n]
