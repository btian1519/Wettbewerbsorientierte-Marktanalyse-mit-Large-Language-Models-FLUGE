from __future__ import annotations

import pytest

from backend.analysis.engine import ScoredRoute
from backend.analysis.market import is_valid_for_scope, validate_scope
from backend.dto import FilterSettings
from backend.filters import apply_filters
from backend.ranking import rank_scored
from shared.constants import Task
from tests.factories import route


def _scored(benefit: float) -> ScoredRoute:
    return ScoredRoute(route=route(), price_eur=100, price_source="x",
                       delta_pax=0.0, benefit_eur=benefit, airline_share=0.0)


def test_ranking_opportunities_maximises():
    ranked = rank_scored([_scored(10), _scored(50), _scored(-5)], Task.OPPORTUNITIES)
    assert [s.benefit_eur for s in ranked] == [50, 10, -5]


def test_ranking_overcapacities_minimises():
    ranked = rank_scored([_scored(10), _scored(-50), _scored(-5)], Task.OVERCAPACITIES)
    assert [s.benefit_eur for s in ranked] == [-50, -5, 10]


def test_filters_min_distance_efficiency():
    near = route(rid=1, distance=2000)   # efficiency 1.0
    far = route(rid=2, distance=11000)   # efficiency 0.1
    kept = apply_filters([near, far], FilterSettings(min_distance_efficiency=0.5))
    assert [r.id for r in kept] == [1]


def test_validate_scope():
    validate_scope("Europe")
    with pytest.raises(ValueError):
        validate_scope("Atlantis")


def test_scope_invariants():
    intra = route(origin_cont="Europe", dest_cont="Europe", scope="Europe")
    inter = route(origin_cont="Europe", dest_cont="Asia", scope="Global/Intercontinental")
    assert is_valid_for_scope(intra, "Europe")
    assert not is_valid_for_scope(intra, "Global/Intercontinental")
    assert is_valid_for_scope(inter, "Global/Intercontinental")
    assert not is_valid_for_scope(inter, "Europe")
