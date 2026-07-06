from __future__ import annotations

import math

from shared.utils import clamp, extract_iata, format_eur, haversine_km, initial_bearing_deg


def test_haversine_known_distance():
    # Frankfurt-ish to Paris-ish ~ 480 km
    d = haversine_km(50.0, 8.0, 48.0, 2.0)
    assert 400 < d < 560


def test_haversine_zero():
    assert haversine_km(10, 20, 10, 20) == 0.0


def test_bearing_east():
    b = initial_bearing_deg(0, 0, 0, 10)
    assert abs(b - 90) < 1e-6


def test_extract_iata():
    assert extract_iata("Munich (MUC)") == "MUC"
    assert extract_iata("no code here") is None
    assert extract_iata("") is None


def test_clamp():
    assert clamp(5, 0, 1) == 1
    assert clamp(-3, 0, 1) == 0
    assert clamp(0.5, 0, 1) == 0.5


def test_format_eur():
    assert format_eur(2_500_000) == "€2.50M"
    assert format_eur(-2_500_000) == "-€2.50M"
    assert format_eur(1500) == "€1.5K"
    assert format_eur(42) == "€42"
