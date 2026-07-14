"""Coordinate-based continent classification.

The ``Continent`` column in ``AIRPORTS.xlsx`` is unreliable — e.g. airports in
Alaska (lat 60, lon -151) are labelled "Africa", which otherwise produces
absurd ~17,000 km "intra-continental" routes. Because the *coordinates* in the
file are trustworthy, we derive each airport's continent from its lat/lon so that
route scopes (and the map) are geographically consistent.

This is data cleaning, not hard-coding airports: no airport is defined here, we
only classify the file's own coordinates into the six required continents using
coarse regional boxes. Border cases (±1-2°) are unavoidable with box tests but
have no material effect on the demo — the point is to eliminate gross errors.
"""

from __future__ import annotations


def continent_from_coords(lat: float, lon: float) -> str | None:
    """Return one of the six continents for a coordinate, or ``None`` if outside
    every region (caller should then fall back to the file label)."""
    # --- Oceania: Australia, NZ, Melanesia (incl. PNG), Pacific (both sides) ---
    if lat <= -10 and (lon >= 110 or lon <= -140):
        return "Oceania"
    if -12 <= lat <= 0 and 140 <= lon <= 170:
        return "Oceania"  # Papua New Guinea / Solomon Islands
    if -30 <= lat <= 25 and (lon >= 155 or lon <= -130):
        return "Oceania"  # Pacific islands (Fiji, Samoa, Tahiti, Guam, ...)

    # --- Western hemisphere: the Americas ---
    if -60 <= lat <= 85 and -170 <= lon <= -30:
        # Central America / Caribbean boundary ~12N; Panama down to ~7N.
        if lat >= 12 or (lat >= 7 and lon <= -77):
            return "North America"
        return "South America"

    # --- Eastern hemisphere ---
    # Mascarene islands (Réunion, Mauritius) belong to the African region.
    if -25 <= lat <= -18 and 52 <= lon <= 58:
        return "Africa"
    if 36 <= lat <= 73 and -31 <= lon <= 44:
        return "Europe"
    if -38 <= lat < 36 and -26 <= lon <= 52:
        return "Africa"
    if lat >= 5 and 40 <= lon <= 180:
        return "Asia"
    if -11 <= lat < 5 and 92 <= lon <= 141:
        return "Asia"  # Indonesia / Malaysia
    return None
