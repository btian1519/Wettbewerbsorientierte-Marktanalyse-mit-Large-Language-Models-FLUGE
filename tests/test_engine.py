from __future__ import annotations

from backend.analysis.engine import BenefitEngine, distance_efficiency, marge_proxy
from backend.dto import FilterSettings
from shared.constants import Task
from tests.factories import offer, route


def test_distance_efficiency_peaks_at_2000():
    assert distance_efficiency(2000) == 1.0
    assert distance_efficiency(12000) == 0.0
    assert distance_efficiency(22000) == 0.0  # clamped, never negative
    assert 0.0 < distance_efficiency(4000) < 1.0


def test_marge_proxy():
    # network=1, distance=2000 -> 0.5*1 + 0.5*1 = 1.0
    assert marge_proxy(1.0, 2000) == 1.0
    # network=0, distance=2000 -> 0.5*0 + 0.5*1 = 0.5
    assert marge_proxy(0.0, 2000) == 0.5


def test_opportunity_uses_full_delta():
    r = route(demand=5000, offers=())  # unserved => supply 0
    eng = BenefitEngine()
    f = FilterSettings()  # marge_average=0.2, network=1.0
    sr = eng.score(r, price_eur=100.0, price_source="x", filters=f,
                   task=Task.OPPORTUNITIES, airline_iata="LH")
    # delta = 5000 - 0; benefit = 5000 * 1.0 * 0.2 * 100 = 100000
    assert sr.delta_pax == 5000
    assert sr.benefit_eur == 5000 * 1.0 * 0.2 * 100
    assert sr.airline_share == 0.0


def test_overcapacity_applies_airline_share():
    offers = (offer("LH", 2000, 150), offer("AF", 1000, 150))  # total supply 3000
    r = route(demand=1000, offers=offers)  # delta_full = 1000-3000 = -2000
    eng = BenefitEngine()
    f = FilterSettings()
    sr = eng.score(r, price_eur=150.0, price_source="airline", filters=f,
                   task=Task.OVERCAPACITIES, airline_iata="LH")
    share = 2000 / 3000
    assert abs(sr.airline_share - share) < 1e-9
    # delta and benefit scaled by LH's share
    assert abs(sr.delta_pax - (-2000 * share)) < 1e-6
    proxy = marge_proxy(1.0, 2000.0)
    expected_benefit = (-2000) * proxy * 0.2 * 150 * share
    assert abs(sr.benefit_eur - expected_benefit) < 1e-6
