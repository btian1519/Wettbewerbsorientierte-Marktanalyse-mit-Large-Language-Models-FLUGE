"""Normalization layer: raw records → ORM-shaped / scored rows.

Pure, dependency-light functions (no DB, no network) so they are fully
unit-testable.
"""

from ingestion.normalization.demand_normalizer import (
    build_signal_scores,
    robust_normalize,
)
from ingestion.normalization.supply_normalizer import normalize_schedules

__all__ = ["normalize_schedules", "build_signal_scores", "robust_normalize"]
