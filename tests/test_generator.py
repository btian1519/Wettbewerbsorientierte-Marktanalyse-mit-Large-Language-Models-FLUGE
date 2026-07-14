from __future__ import annotations

from types import SimpleNamespace

from database.repository.interfaces import AirlineRead, AirportRead
from ingestion.demo_generator import DemoDataSource
from ingestion.demo_generator.generator import _MIN_ROUTE_KM
from shared.constants import INTERCONTINENTAL


def _airports() -> list[AirportRead]:
    out: list[AirportRead] = []
    # 8 Europe + 8 Asia airports on a grid spaced so every pair is >100 km apart.
    for i in range(8):
        out.append(AirportRead(f"E{i:02d}", f"eu{i}", "X", 5.0 + i * 2.0, 45.0 + i * 1.2, "Europe"))
    for i in range(8):
        out.append(AirportRead(f"A{i:02d}", f"as{i}", "Y", 120.0 + i * 2.0, 25.0 + i * 1.2, "Asia"))
    return out


def _airlines() -> list[AirlineRead]:
    return [
        AirlineRead("LH", "Lufthansa", "Munich (MUC)", "Europe", "MUC"),
        AirlineRead("AF", "Air France", "Paris (CDG)", "Europe", "CDG"),
        AirlineRead("NH", "ANA", "Tokyo (NRT)", "Asia", "NRT"),
    ]


def _settings():
    return SimpleNamespace(
        routes_per_continent=40, intercontinental_routes=40, demo_seed=7, demo_week="2026-W27"
    )


def test_batch_is_internally_consistent():
    batch = DemoDataSource(_airports(), _airlines(), _settings()).produce("2026-W27")
    route_ids = {r["id"] for r in batch.route_rows}

    assert len(route_ids) == len(batch.route_rows)  # unique ids
    for o in batch.offer_rows:
        assert o["route_week_id"] in route_ids
        assert o["capacity"] == o["seats_per_flight"] * o["frequency"]
        assert o["frequency"] >= 1
        assert o["avg_price_eur"] > 0


def test_scope_endpoints_respect_geography():
    batch = DemoDataSource(_airports(), _airlines(), _settings()).produce("2026-W27")
    for r in batch.route_rows:
        if r["scope"] == INTERCONTINENTAL:
            assert r["origin_continent"] != r["dest_continent"]
        else:
            assert r["origin_continent"] == r["dest_continent"] == r["scope"]
        assert r["origin_iata"] != r["dest_iata"]


def test_no_degenerate_short_routes():
    # Every generated route must clear the minimum-distance floor (no 0 km /
    # same-metro pairs).
    batch = DemoDataSource(_airports(), _airlines(), _settings()).produce("2026-W27")
    assert batch.route_rows
    assert all(r["distance_km"] >= _MIN_ROUTE_KM for r in batch.route_rows)


def test_route_count_capped_at_available_pairs():
    # Each continent has 8 airports -> max 8*7 = 56 directed pairs; target 40 fits.
    batch = DemoDataSource(_airports(), _airlines(), _settings()).produce("2026-W27")
    per_scope: dict[str, int] = {}
    for r in batch.route_rows:
        per_scope[r["scope"]] = per_scope.get(r["scope"], 0) + 1
    assert per_scope["Europe"] <= 56
    assert per_scope["Asia"] <= 56


def test_has_both_served_and_unserved_routes():
    batch = DemoDataSource(_airports(), _airlines(), _settings()).produce("2026-W27")
    served_ids = {o["route_week_id"] for o in batch.offer_rows}
    all_ids = {r["id"] for r in batch.route_rows}
    assert served_ids, "expected some served routes"
    assert all_ids - served_ids, "expected some unserved routes (market gaps)"
