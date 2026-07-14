"""Demand model V1 (rule-based) + calibration + confidence."""

from __future__ import annotations

from ingestion.calibration import CalibrationContext, CalibrationLayer
from ingestion.demand.model import RuleBasedDemandModelV1
from ingestion.demand.records import DemandSignals


def test_full_signals_weighted_sum():
    m = RuleBasedDemandModelV1()
    # All components = 100 -> index 100, full coverage.
    sig = DemandSignals(google=100, wikipedia=100, tourism=100, population=100, gdp=100, event=100)
    comp = m.compute(sig)
    assert comp.demand_index == 100.0
    assert comp.weight_coverage == 1.0
    assert comp.calculation_version == "v1"


def test_weights_applied():
    m = RuleBasedDemandModelV1()
    # Only google present (others None = missing) -> renormalized to 100.
    comp = m.compute(DemandSignals(google=100))
    assert comp.demand_index == 100.0
    assert comp.weight_coverage == 0.45


def test_dynamic_reweighting_when_missing():
    m = RuleBasedDemandModelV1()
    # google=80, wikipedia=20; weights 0.45 & 0.15 renormalize to 0.75 & 0.25.
    comp = m.compute(DemandSignals(google=80, wikipedia=20))
    assert abs(comp.demand_index - (0.75 * 80 + 0.25 * 20)) < 1e-6
    assert abs(comp.weight_coverage - 0.60) < 1e-9


def test_empty_signals():
    comp = RuleBasedDemandModelV1().compute(DemandSignals())
    assert comp.demand_index == 0.0 and comp.weight_coverage == 0.0


def test_calibration_factor_and_estimate():
    cal = CalibrationLayer()
    factor = cal.calibration_factor(reference_passengers=5000, reference_index=50)
    assert factor == 100.0
    assert cal.estimate_calibrated(50, factor) == 5000.0


def test_fallback_lower_and_distance_sensitive():
    cal = CalibrationLayer()
    near = cal.fallback_estimate(80, CalibrationContext(distance_km=2000))
    far = cal.fallback_estimate(80, CalibrationContext(distance_km=12000))
    assert near > far > 0


def test_confidence_tiers():
    cal = CalibrationLayer()
    proxy_only = cal.confidence(0.45, calibrated=False, has_history=False)   # google only
    high = cal.confidence(1.0, calibrated=True, has_history=True)            # everything
    assert 0.4 <= proxy_only <= 0.6
    assert high >= 0.9
