from __future__ import annotations

from backend.pricing.pricing import (
    SRC_AIRLINE,
    SRC_DISTANCE_PROXY,
    SRC_ROUTE_OTHERS,
    PriceResolver,
)
from tests.factories import offer, route


def test_priority_1_selected_airline_on_route():
    r = route(offers=(offer("LH", 1000, 199), offer("AF", 1000, 150)))
    res = PriceResolver([r], "LH").resolve(r)
    assert res.source == SRC_AIRLINE
    assert res.price_eur == 199


def test_priority_2_other_airlines_on_route():
    r = route(offers=(offer("AF", 1000, 150), offer("BA", 1000, 250)))
    res = PriceResolver([r], "LH").resolve(r)
    assert res.source == SRC_ROUTE_OTHERS
    assert res.price_eur == 200  # mean of 150 & 250


def test_priority_3_distance_proxy_from_selected_airline():
    priced = route(rid=1, distance=2000, offers=(offer("LH", 1000, 300),))
    target = route(rid=2, origin="CCC", dest="DDD", distance=2100, offers=())  # unserved, similar dist
    res = PriceResolver([priced, target], "LH").resolve(target)
    assert res.source == SRC_DISTANCE_PROXY
    assert res.price_eur == 300
