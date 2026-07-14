from __future__ import annotations

from datetime import date

from ingestion.connectors.records import RawFlightSchedule
from ingestion.demand.records import RawSignal
from ingestion.normalization import (
    build_signal_scores,
    normalize_schedules,
    robust_normalize,
)


# --- Supply normalization (unchanged) ------------------------------------- #
def test_supply_aggregates_per_route_airline():
    schedules = [
        RawFlightSchedule(airline_iata="LH", origin_iata="FRA", dest_iata="MUC",
                          frequency=7, aircraft_type="A320"),
        RawFlightSchedule(airline_iata="LH", origin_iata="FRA", dest_iata="MUC",
                          frequency=3, aircraft_type="A320"),
        RawFlightSchedule(airline_iata="AF", origin_iata="FRA", dest_iata="MUC", frequency=5),
    ]
    rows = normalize_schedules(
        schedules, week="2026-W27", snapshot_date=date(2026, 7, 6),
        resolve_route_id=lambda o, d: 1, seats_for=lambda t: 180,
    )
    by_airline = {r["airline_iata"]: r for r in rows}
    assert by_airline["LH"]["frequency"] == 10
    assert by_airline["LH"]["available_seats"] == 10 * 180


# --- Demand normalization (0..100, robust) -------------------------------- #
def test_robust_normalize_scales_to_0_100():
    out = robust_normalize([0, 50, 100])
    assert out[0] == 0.0 and out[-1] == 100.0


def test_robust_normalize_is_outlier_resistant():
    # 100 normal values (1..100) plus two extreme outliers (~2% of the sample):
    # percentile clipping caps the outliers so they don't crush the rest to 0.
    values = list(range(1, 101)) + [10**6, 10**6]
    out = robust_normalize(values)
    assert out[-1] == 100.0 and out[-2] == 100.0   # both outliers clipped to the top
    assert 30 < out[49] < 70                        # the value 50 stays mid-range


def test_robust_normalize_degenerate():
    assert robust_normalize([5, 5, 5]) == [50.0, 50.0, 50.0]


def test_build_signal_scores_maps_components():
    signals = [
        RawSignal(origin_airport="AAA", destination_airport="BBB", signal_type="google_trends",
                  signal_value=80, source="google_trends"),
        RawSignal(origin_airport="AAA", destination_airport="BBB", signal_type="wikipedia_views",
                  signal_value=5000, source="wikipedia"),
        RawSignal(origin_airport="CCC", destination_airport="DDD", signal_type="google_trends",
                  signal_value=20, source="google_trends"),
    ]
    scores = build_signal_scores(signals)
    aab = scores[("AAA", "BBB")]
    assert aab.google == 100.0        # highest google value across routes
    assert aab.wikipedia is not None  # only one wiki value -> degenerate 50
    assert scores[("CCC", "DDD")].google == 0.0
