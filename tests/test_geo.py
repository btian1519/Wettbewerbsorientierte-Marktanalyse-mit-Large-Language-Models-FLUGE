from __future__ import annotations

import pytest

from shared.geo import continent_from_coords


@pytest.mark.parametrize(
    "lat, lon, expected",
    [
        (52.5, 13.4, "Europe"),        # Berlin
        (33.6, -7.6, "Africa"),        # Casablanca
        (35.7, 139.7, "Asia"),         # Tokyo
        (25.3, 55.4, "Asia"),          # Dubai
        (-33.9, 151.2, "Oceania"),     # Sydney
        (-36.8, 174.8, "Oceania"),     # Auckland
        (40.6, -73.8, "North America"),  # New York
        (60.0, -151.0, "North America"),  # Alaska (the file mislabels this "Africa")
        (-23.5, -46.6, "South America"),  # São Paulo
        (-20.9, 55.5, "Africa"),       # Réunion (Mascarene)
        (-9.4, 147.2, "Oceania"),      # Port Moresby (PNG)
    ],
)
def test_continent_from_coords(lat, lon, expected):
    assert continent_from_coords(lat, lon) == expected


def test_alaska_is_not_africa():
    # Regression: the source file tags Alaskan airports as "Africa"; the
    # coordinate classifier must correct that to North America.
    assert continent_from_coords(60.0, -151.0) == "North America"
